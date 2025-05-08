from typing import Any

from robot.utils import Secret


def get_secret(value: str = "This is a secret", name: "None|str"=None) -> Secret:
    return Secret(value, name)


def receive_secret(secret: Secret) -> Any:
    return secret.value
