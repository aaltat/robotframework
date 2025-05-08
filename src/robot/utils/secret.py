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


class Secret:
    type = None

    def __init__(self, value, name=None):
        self.__value = value
        self.name = name

    @property
    def value(self):
        return self.type(self.__value) if self.type else self.__value

    @classmethod
    def __class_getitem__(cls, item):
        return type(f"{cls.__name__}[{item.__name__}]", (cls,), {"type": item})

    def __str__(self):
        name = type(self).__name__
        args = "value=<secret>"
        if self.name:
            args += f", name={self.name!r}"
        return f"{name}({args})"
