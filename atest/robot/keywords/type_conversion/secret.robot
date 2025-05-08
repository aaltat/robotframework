*** Settings ***
Suite Setup       Run Tests    ${EMPTY}    keywords/type_conversion/secret.robot
Resource          atest_resource.robot

*** Test Cases ***
Create: Library keyword
    Check Test Case    ${TESTNAME}

Create: Env variable
    Check Test Case    ${TESTNAME}

Create: List
    Check Test Case    ${TESTNAME}

Create: Dictionary
    Check Test Case    ${TESTNAME}

User keyword
    Check Test Case    ${TESTNAME}

User keyword: Receive not secret
    Check Test Case    ${TESTNAME}

User keyword: Receive not secret var
    Check Test Case    ${TESTNAME}

Library keyword
    Check Test Case    ${TESTNAME}

Library keyword: not secret 1
    Check Test Case    ${TESTNAME}

Library keyword: not secret 2
    Check Test Case    ${TESTNAME}
