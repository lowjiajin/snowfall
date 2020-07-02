from abc import ABC, abstractmethod


class AbstractAssigner(ABC):

    @abstractmethod
    def claim_generator_id(self, *args, **kwargs):
        pass

    @abstractmethod
    def get_epoch_start(self, *args, **kwargs):
        pass
