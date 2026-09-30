from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class ConfiguredRootStorage(FileSystemStorage):
    def __init__(self, root_setting):
        self.root_setting = root_setting
        super().__init__()

    @property
    def location(self):
        return str(getattr(settings, self.root_setting))