class Singleton(type):
    # TODO NOT WORKING
    __unique_instance = None

    def __call__(cls, *args, **kwargs):
        """
        Override the __call__ method to make sure only one instance is created.
        """
        if cls.__unique_instance is None:
            cls.__instance = type.__call__(cls, *args, **kwargs)

        return cls.__instance
