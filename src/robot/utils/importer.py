#  Copyright 2008-2015 Nokia Networks
#  Copyright 2016-     Robot Framework Foundation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import importlib
import inspect
import os.path
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from robot.errors import DataError

from .error import get_error_details
from .robotinspect import is_init
from .robotpath import abspath, normpath
from .robottypes import type_name


class Importer:
    """Utility that can import modules and classes based on names and paths.

    Imported classes can optionally be instantiated automatically.
    """

    def __init__(self, type=None, logger=None):
        """
        :param type:
            Type of the thing being imported. Used in error and log messages.
        :param logger:
            Logger to be notified about successful imports and other events.
            Currently only needs the ``info`` method, but other level specific
            methods may be needed in the future. If not given, logging is disabled.
        """
        self.type = type or ""
        self.logger = logger or NoLogger()
        library_import = type and type.upper() == "LIBRARY"
        self._importers = (
            ByPathImporter(self.logger, library_import),
            NonDottedImporter(self.logger, library_import),
            DottedImporter(self.logger, library_import),
        )
        self._by_path_importer = self._importers[0]

    def import_class_or_module(
        self,
        name_or_path: "str|Path",
        instantiate_with_args: "Sequence|None" = None,
        return_source: bool = False,
    ):
        """Imports Python class or module based on the given name or path.

        :param name_or_path:
            Name or path of the module or class to import. If a path is given as
            a string, it must be absolute. Paths given as ``Path`` objects can be
            relative starting from Robot Framework 7.3.
        :param instantiate_with_args:
            When arguments are given, imported classes are automatically initialized
            using them.
        :param return_source:
            When true, returns a tuple containing the imported module or class
            and a path to it. By default, returns only the imported module or class.

        The class or module to import can be specified either as a name, in which
        case it must be in the module search path, or as a path to the file or
        directory implementing the module. See :meth:`import_class_or_module_by_path`
        for more information about importing classes and modules by path.

        Classes can be imported from the module search path using name like
        ``modulename.ClassName``. If the class name and module name are same, using
        just ``CommonName`` is enough. When importing a class by a path, the class
        name and the module name must match.

        Optional arguments to use when creating an instance are given as a list.
        Starting from Robot Framework 4.0, both positional and named arguments are
        supported (e.g. ``['positional', 'name=value']``) and arguments are converted
        automatically based on type hints and default values.

        If arguments needed when creating an instance are initially embedded into
        the name or path like ``Example:arg1:arg2``, separate
        :func:`~robot.utils.text.split_args_from_name_or_path` function can be
        used to split them before calling this method.

        Use :meth:`import_module` if only a module needs to be imported.
        """
        try:
            imported, source = self._import(name_or_path)
            self._log_import_succeeded(imported, name_or_path, source)
            imported = self._instantiate_if_needed(imported, instantiate_with_args)
        except DataError as err:
            self._raise_import_failed(name_or_path, err)
        else:
            return self._handle_return_values(imported, source, return_source)

    def import_module(self, name_or_path: "str|Path"):
        """Imports Python module based on the given name or path.

        :param name_or_path:
            Name or path of the module to import. If a path is given as a string,
            it must be absolute. Paths given as ``Path`` objects can be relative
            starting from Robot Framework 7.3.

        The module to import can be specified either as a name, in which
        case it must be in the module search path, or as a path to the file or
        directory implementing the module. See :meth:`import_class_or_module_by_path`
        for more information about importing modules by path.

        Use :meth:`import_class_or_module` if it is desired to get a class
        from the imported module automatically.

        New in Robot Framework 6.0.
        """
        try:
            imported, source = self._import(name_or_path, get_class=False)
            self._log_import_succeeded(imported, name_or_path, source)
        except DataError as err:
            self._raise_import_failed(name_or_path, err)
        else:
            return imported

    def _import(self, name, get_class=True):
        for importer in self._importers:
            if importer.handles(name):
                return importer.import_(name, get_class)
        assert False

    def _handle_return_values(self, imported, source, return_source=False):
        if not return_source:
            return imported
        if source and os.path.exists(source):
            source = self._sanitize_source(source)
        return imported, source

    def _sanitize_source(self, source):
        source = normpath(source)
        if os.path.isdir(source):
            candidate = os.path.join(source, "__init__.py")
        elif source.endswith(".pyc"):
            candidate = source[:-4] + ".py"
        else:
            return source
        return candidate if os.path.exists(candidate) else source

    def import_class_or_module_by_path(
        self,
        path: "str|Path",
        instantiate_with_args: "Sequence|None" = None,
    ):
        """Import a Python module or class using a file system path.

        :param path:
            Path to the module or class to import. If a path is given as a string,
            it must be absolute. Paths given as ``Path`` objects can be relative
            starting from Robot Framework 7.3.
        :param instantiate_with_args:
            When arguments are given, imported classes are automatically initialized
            using them.

        When importing a Python file, the path must end with :file:`.py` and the
        actual file must also exist.

        Use :meth:`import_class_or_module` to support importing also using name,
        not only path. See the documentation of that function for more information
        about creating instances automatically.
        """
        try:
            imported, source = self._by_path_importer.import_(path)
            self._log_import_succeeded(imported, imported.__name__, source)
            return self._instantiate_if_needed(imported, instantiate_with_args)
        except DataError as err:
            self._raise_import_failed(path, err)

    def _log_import_succeeded(self, item, name, source):
        prefix = f"Imported {self.type.lower()}" if self.type else "Imported"
        item_type = "module" if inspect.ismodule(item) else "class"
        source = f"'{source}'" if source else "unknown location"
        self.logger.info(f"{prefix} {item_type} '{name}' from {source}.")

    def _raise_import_failed(self, name, error) -> NoReturn:
        prefix = f"Importing {self.type.lower()}" if self.type else "Importing"
        raise DataError(f"{prefix} '{name}' failed: {error}")

    def _instantiate_if_needed(self, imported, args):
        if args is None:
            return imported
        if inspect.isclass(imported):
            return self._instantiate_class(imported, args)
        if args:
            raise DataError("Modules do not take arguments.")
        return imported

    def _instantiate_class(self, imported, args):
        spec = self._get_arg_spec(imported)
        try:
            positional, named = spec.resolve(args)
        except ValueError as err:
            raise DataError(err.args[0])
        try:
            return imported(*positional, **dict(named))
        except Exception:
            message, traceback = get_error_details()
            raise DataError(f"Creating instance failed: {message}\n{traceback}")

    def _get_arg_spec(self, imported):
        # Avoid cyclic import. Yuck.
        from robot.running.arguments import ArgumentSpec, PythonArgumentParser

        init = getattr(imported, "__init__", None)
        name = imported.__name__
        if not is_init(init):
            return ArgumentSpec(name, self.type)
        return PythonArgumentParser(self.type).parse(init, name)


class _Importer:

    def __init__(self, logger, library_import=False):
        self.logger = logger
        self.library_import = library_import

    def _import(self, name, fromlist=None):
        if name in sys.builtin_module_names:
            raise DataError(
                "Cannot import custom module with same name as Python built-in module."
            )
        importlib.invalidate_caches()
        try:
            return __import__(name, fromlist=fromlist)
        except Exception:
            message, traceback = get_error_details(full_traceback=False)
            path = "\n".join(f"  {p}" for p in sys.path)
            raise DataError(f"{message}\n{traceback}\nPYTHONPATH:\n{path}")

    def _verify_type(self, imported):
        if inspect.isclass(imported) or inspect.ismodule(imported):
            return imported
        raise DataError(f"Expected class or module, got {type_name(imported)}.")

    def _get_possible_class(self, module, name=None):
        cls = self._get_class_matching_module_name(module, name)
        if not cls and self.library_import:
            cls = self._get_decorated_library_class_in_imported_module(module)
        return cls or module

    def _get_class_matching_module_name(self, module, name):
        cls = getattr(module, name or module.__name__, None)
        return cls if inspect.isclass(cls) else None

    def _get_decorated_library_class_in_imported_module(self, module):
        def predicate(item):
            return (
                inspect.isclass(item)
                and hasattr(item, "ROBOT_AUTO_KEYWORDS")
                and item.__module__ == module.__name__
            )

        classes = [cls for _, cls in inspect.getmembers(module, predicate)]
        return classes[0] if len(classes) == 1 else None

    def _get_source(self, imported):
        try:
            source = inspect.getfile(imported)
        except TypeError:
            return None
        return abspath(source) if source else None


class ByPathImporter(_Importer):
    _valid_import_extensions = (".py", "")

    def handles(self, path):
        return os.path.isabs(path) or isinstance(path, Path)

    def import_(self, path, get_class=True):
        path = self._verify_import_path(path)
        self._remove_wrong_module_from_sys_modules(path)
        imported = self._import_by_path(path)
        if get_class:
            imported = self._get_possible_class(imported)
        return self._verify_type(imported), path

    def _verify_import_path(self, path):
        if not os.path.exists(path):
            raise DataError("File or directory does not exist.")
        if not os.path.isabs(path):
            if isinstance(path, Path):
                path = path.absolute()
            else:
                raise DataError("Import path must be absolute.")
        if os.path.splitext(path)[1] not in self._valid_import_extensions:
            raise DataError("Not a valid file or directory to import.")
        return os.path.normpath(path)

    def _remove_wrong_module_from_sys_modules(self, path):
        importing_from, name = self._split_path_to_module(path)
        importing_package = os.path.splitext(path)[1] == ""
        if self._wrong_module_imported(name, importing_from, importing_package):
            del sys.modules[name]
            self.logger.info(
                f"Removed module '{name}' from sys.modules to import a fresh module."
            )

    def _split_path_to_module(self, path):
        module_dir, module_file = os.path.split(abspath(path))
        module_name = os.path.splitext(module_file)[0]
        return module_dir, module_name

    def _wrong_module_imported(self, name, importing_from, importing_package):
        if name not in sys.modules:
            return False
        source = getattr(sys.modules[name], "__file__", None)
        if not source:  # play safe
            return True
        imported_from, imported_package = self._get_import_information(source)
        return (
            normpath(importing_from, case_normalize=True)
            != normpath(imported_from, case_normalize=True)
            or importing_package != imported_package
        )

    def _get_import_information(self, source):
        imported_from, imported_file = self._split_path_to_module(source)
        imported_package = imported_file == "__init__"
        if imported_package:
            imported_from = os.path.dirname(imported_from)
        return imported_from, imported_package

    def _import_by_path(self, path):
        module_dir, module_name = self._split_path_to_module(path)
        sys.path.insert(0, module_dir)
        try:
            return self._import(module_name)
        finally:
            sys.path.remove(module_dir)


class NonDottedImporter(_Importer):

    def handles(self, name):
        return "." not in name

    def import_(self, name, get_class=True):
        imported = self._import(name)
        if get_class:
            imported = self._get_possible_class(imported)
        return self._verify_type(imported), self._get_source(imported)


class DottedImporter(_Importer):

    def handles(self, name):
        return "." in name

    def import_(self, name, get_class=True):
        parent_name, lib_name = name.rsplit(".", 1)
        parent = self._import(parent_name, fromlist=[str(lib_name)])
        try:
            imported = getattr(parent, lib_name)
        except AttributeError:
            raise DataError(f"Module '{parent_name}' does not contain '{lib_name}'.")
        if get_class:
            imported = self._get_possible_class(imported, lib_name)
        return self._verify_type(imported), self._get_source(imported)


class NoLogger:
    error = warn = info = debug = trace = lambda self, *args, **kws: None
