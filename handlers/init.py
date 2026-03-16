"""
Пакет с обработчиками для MAX
"""
from .start import *
from .modes import *
from .goals import *
from .reality import *
from .questions import *
from .profile import *
from .routes import *
from .help import *
from .admin import *
from .context import *
from .stages import *

# Для удобства можно добавить список всех модулей
__all__ = [
    'start', 'modes', 'goals', 'reality', 
    'questions', 'profile', 'routes', 'help', 
    'admin', 'context', 'stages'
]
