import queue
import threading
from functools import partial
from threading import Thread
from typing import Any

from nfvcl.blueprints_ng.blueprint_ng import BlueprintNG, BlueprintNGStatus, CurrentOperation
from nfvcl.blueprints_ng.lcm.blueprint_type_manager import blueprint_type
from nfvcl.blueprints_ng.lcm.performance_manager import get_performance_manager
from nfvcl.models.blueprint_ng.worker_message import WorkerMessageType, WorkerMessage, BlueprintOperationCallbackModel
from nfvcl.models.performance import BlueprintPerformanceType
from nfvcl.utils.log import create_logger
from nfvcl.utils.redis_utils.redis_manager import trigger_redis_event
from nfvcl.utils.redis_utils.topic_list import BLUEPRINT_TOPIC
from nfvcl.utils.redis_utils.event_types import BlueEventType


def callback_function(event, namespace, msg: BlueprintOperationCallbackModel):
    namespace["msg"] = msg
    event.set()


class BlueprintWorker:
    blueprint: BlueprintNG
    message_queue: queue.Queue
    thread: Thread = None

    def __init__(self, blueprint: BlueprintNG):
        self.blueprint = blueprint
        self.logger = create_logger('BLUEV2_WORKER', blueprintid=blueprint.id)
        self.message_queue = queue.Queue()

    def start_listening(self):
        self.thread = Thread(target=self._listen, args=())
        self.thread.start()

    def stop_listening(self):
        self.logger.info("Blueprint worker stopping listening.")

    def call_function_sync(self, function_name, *args, **kwargs) -> BlueprintOperationCallbackModel:
        """
        Call a function synchronously
        Args:
            function_name: Name of the function to call
            *args: args
            **kwargs: kwargs

        Returns: return value of the function
        """
        # used to wait for the call to be completed
        event = threading.Event()
        # used to receive the return data from the function
        namespace = {}

        self.put_message(WorkerMessageType.DAY2_BY_NAME, function_name, (args, kwargs), callback=partial(callback_function, event, namespace))
        event.wait()

        return namespace["msg"]

    def put_message_sync(self, msg_type: WorkerMessageType, path: str, message: Any):
        # used to wait for the call to be completed
        event = threading.Event()
        # used to receive the return data from the function
        namespace = {}

        self.put_message(msg_type, path, message, callback=partial(callback_function, event, namespace))
        event.wait()

        return namespace["msg"]

    def put_message(self, msg_type: WorkerMessageType, path: str, message: Any, callback: callable = None):
        """
        Insert the worker message into the queue. This function should be called by an external process to the worker.
        THREAD SAFE.

        Args:
            msg_type: The type of the message (DAY0 (creation), DAY2, STOP)
            path: The path of the request.
            message: The message of the request.
            callback: Function to be called after the message is processed
        """
        worker_message = WorkerMessage(message_type=msg_type, message=message, path=path, callback=callback)
        self.message_queue.put(worker_message)  # Thread safe

    def destroy_blueprint_sync(self):
        """
        Sent a termination message to the worker. This function should be called by an external process to the worker.
        """
        self.put_message_sync(WorkerMessageType.STOP, message="", path="")

    def destroy_blueprint(self):
        """
        Sent a termination message to the worker. This function should be called by an external process to the worker.
        """
        worker_message = WorkerMessage(message_type=WorkerMessageType.STOP, message="", path="")
        self.message_queue.put(worker_message)  # Thread safe

    def protect_blueprint(self, protect: bool) -> bool:
        """
        Change the protected status given the desired one.
        Args:
            protect: true if the blueprint is protected from deletion.

        Returns:
            The new protected value in state.
        """
        self.blueprint.base_model.protected = protect
        self.blueprint.to_db()
        return self.blueprint.base_model.protected

    def _listen(self):
        self.logger.debug(f"Worker listening")
        while True:
            received_message: WorkerMessage = self.message_queue.get()  # Thread safe
            self.logger.debug(f"Received message: {received_message.message}")
            match received_message.message_type:
                # ------------------------ This is the case of blueprint creation (create and start VMs, Dockers, ...)
                case WorkerMessageType.DAY0:
                    self.logger.info(f"Creating blueprint")
                    self.blueprint.base_model.status = BlueprintNGStatus.deploying(self.blueprint.id)
                    trigger_redis_event(BLUEPRINT_TOPIC, BlueEventType.BLUE_STARTED_DAY0, self.blueprint.base_model.model_dump())
                    self.blueprint.to_db()
                    try:
                        performance_operation_id = get_performance_manager().start_operation(self.blueprint.id, BlueprintPerformanceType.DAY0, "create")
                        self.blueprint.create(received_message.message)
                        get_performance_manager().end_operation(performance_operation_id)
                        if received_message.callback:
                            received_message.callback(BlueprintOperationCallbackModel(id=self.blueprint.id, operation=str(CurrentOperation.IDLE), status="OK"))
                        self.blueprint.base_model.status = BlueprintNGStatus(current_operation=CurrentOperation.IDLE)
                        trigger_redis_event(BLUEPRINT_TOPIC, BlueEventType.BLUE_CREATED, self.blueprint.base_model.model_dump())
                        self.logger.success(f"Blueprint created")
                    except Exception as e:
                        self.blueprint.base_model.status.error = True
                        self.blueprint.base_model.status.detail = str(e)
                        if received_message.callback:
                            received_message.callback(BlueprintOperationCallbackModel(id=self.blueprint.id, operation=str(CurrentOperation.IDLE), status="ERROR", detailed_status=str(e)))
                        self.logger.error(f"Error creating blueprint", exc_info=e)
                        trigger_redis_event(BLUEPRINT_TOPIC, BlueEventType.BLUE_ERROR, self.blueprint.base_model.model_dump())

                    self.blueprint.to_db()
                # ------------------------- This is the case of blueprint day 2
                case WorkerMessageType.DAY2 | WorkerMessageType.DAY2_BY_NAME:
                    self.logger.info(f"Calling DAY2 function on blueprint")
                    self.blueprint.base_model.status = BlueprintNGStatus(current_operation=CurrentOperation.RUNNING_DAY2_OP, detail=f"Calling DAY2 function {received_message.path} on blueprint {self.blueprint.id}")
                    trigger_redis_event(BLUEPRINT_TOPIC, BlueEventType.BLUE_STARTED_DAY2, self.blueprint.base_model.model_dump())
                    self.blueprint.to_db()
                    try:
                        # This is the DAY2 message, getting the function to be called
                        if received_message.message_type == WorkerMessageType.DAY2:
                            if received_message.message:
                                self.blueprint.base_model.day_2_call_history.append(received_message.message.model_dump_json())
                            function = blueprint_type.get_function_to_be_called(received_message.path)
                            performance_operation_id = get_performance_manager().start_operation(self.blueprint.id, BlueprintPerformanceType.DAY2, received_message.path.split("/")[-1])
                            if received_message.message:
                                result = getattr(self.blueprint, function.__name__)(received_message.message)
                            else:
                                result = getattr(self.blueprint, function.__name__)()
                            get_performance_manager().end_operation(performance_operation_id)
                        else:
                            performance_operation_id = get_performance_manager().start_operation(self.blueprint.id, BlueprintPerformanceType.DAY2, received_message.path.split("/")[-1])
                            result = getattr(self.blueprint, received_message.path)(*received_message.message[0], **received_message.message[1])
                            get_performance_manager().end_operation(performance_operation_id)

                        # Starting processing the request.
                        if received_message.callback:
                            received_message.callback(BlueprintOperationCallbackModel(id=self.blueprint.id, operation=str(CurrentOperation.IDLE), result=result, status="OK"))

                        self.blueprint.base_model.status = BlueprintNGStatus(current_operation=CurrentOperation.IDLE)
                        trigger_redis_event(BLUEPRINT_TOPIC, BlueEventType.BLUE_END_DAY2, self.blueprint.base_model.model_dump())
                        self.logger.success(f"Function DAY2 {received_message.path} on blueprint {self.blueprint.id} called.")
                    except Exception as e:
                        self.blueprint.base_model.status.error = True
                        self.blueprint.base_model.status.detail = str(e)
                        if received_message.callback:
                            received_message.callback(BlueprintOperationCallbackModel(id=self.blueprint.id, operation=str(CurrentOperation.IDLE), status="ERROR", detailed_status=str(e)))
                        self.logger.error(f"Error calling function on blueprint", exc_info=e)
                        trigger_redis_event(BLUEPRINT_TOPIC, BlueEventType.BLUE_ERROR, self.blueprint.base_model.model_dump())
                    self.blueprint.to_db()
                # ------------------------- This is the case of blueprint destroy
                case WorkerMessageType.STOP:
                    self.logger.info(f"Destroying blueprint")
                    self.blueprint.base_model.status = BlueprintNGStatus.destroying(blue_id=self.blueprint.id)
                    trigger_redis_event(BLUEPRINT_TOPIC, BlueEventType.BLUE_START_DAYN, self.blueprint.base_model.model_dump())
                    performance_operation_id = get_performance_manager().start_operation(self.blueprint.id, BlueprintPerformanceType.DELETION, "delete")
                    self.blueprint.destroy()
                    get_performance_manager().end_operation(performance_operation_id)
                    if received_message.callback:
                        received_message.callback(self.blueprint.id)
                    self.logger.success(f"Blueprint destroyed")
                    trigger_redis_event(BLUEPRINT_TOPIC, BlueEventType.BLUE_DELETED, self.blueprint.base_model.model_dump())
                    break
                case _:
                    raise ValueError("Worker message type not recognized")

        self.stop_listening()

    def __eq__(self, __value):
        """
        Allow finding duplicate workers. Two workers are equivalent if built on the same blueprint (if blue.id is the same)
        Args:
            __value: (BlueprintWorker) The object to be compared
        """
        if isinstance(__value, BlueprintWorker):
            if self.blueprint.base_model.id == __value.blueprint.base_model.id:
                return True
        return False
