

class SQLCommandType:

    SELECT = 'select'
    INSERT = 'insert'
    UPDATE = 'update'
    DELETE = 'delete'

    VALUES = (SELECT, INSERT, UPDATE, DELETE)


class DbStatus:

    ACTIVE = 'active'
    NOT_EXISTS = 'not exists'

    VALUES = (ACTIVE, NOT_EXISTS)


class DebugFormat:

    TABULAR = 'tabular'
    ARRAY = 'array'

    VALUES = (TABULAR, ARRAY)
