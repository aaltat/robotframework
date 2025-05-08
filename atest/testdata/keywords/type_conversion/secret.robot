*** Settings ***
Library     secret.py
Library     OperatingSystem

*** Variables ***
${SECRET: secret}    value of secret here


*** Test Cases ***
Create: Library keyword
    ${secret}    Get Secret
    ${secret: Secret}    Get Secret    value of secret here    name_is_here

Create: Env variable
    Set Environment Variable    SECRET    VALUE
    VAR    ${secret: secret}    %{SECRET}

Create: List
    ${secret}    Get Secret
    VAR    @{x: secret}   ${secret}    ${secret}
    VAR    @{x: int|secret}   1    ${secret}    3

Create: Dictionary
    ${secret}    Get Secret
    VAR    &{x: secret}   key=${secret}
    VAR    &{x: int=secret}   42=${secret}

User keyword
    ${x: secret}    Return secret

User keyword: Receive not secret
    [Documentation]    FAIL
    ...    ValueError: Argument 'secret' got value 'xxx' that cannot be converted to Secret: \
    ...    Secret type cannot be converted. Use Secret(value) instead.
    Receive Secret    xxx

User keyword: Receive not secret var
    [Documentation]    FAIL
    ...    ValueError: Argument 'secret' got value 'y' that cannot be converted to Secret: \
    ...    Secret type cannot be converted. Use Secret(value) instead.
    VAR    ${x}    y
    Receive Secret    ${x}

Library keyword
    ${secret: secret}    Get Secret
    Receive Secret    ${secret}

Library keyword: not secret 1
    [Documentation]    FAIL
    ...    ValueError: Argument 'secret' got value '111' that cannot be converted to Secret: \
    ...    Secret type cannot be converted. Use Secret(value) instead.
    Receive Secret    111

Library keyword: not secret 2
    [Documentation]    FAIL
    ...    ValueError: Argument 'secret' got value '222' that cannot be converted to Secret: \
    ...    Secret type cannot be converted. Use Secret(value) instead.
    VAR    ${x}    222
    Receive Secret    ${x}

*** Keywords ***
Receive secret
    [Arguments]    ${secret: secret}
    Log    ${secret}

Return secret
    ${secret}    Get Secret
    RETURN    ${secret}
