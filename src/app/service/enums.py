

class SQLCommandType:

    SELECT = 'select'
    DELETE = 'delete'

    CHOICES = (
        (SELECT, SELECT),
        (DELETE, DELETE),
    )
