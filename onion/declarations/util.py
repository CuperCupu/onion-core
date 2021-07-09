from contextlib import contextmanager
from typing import Union, Iterable, Any

from pydantic import ValidationError
from pydantic.error_wrappers import ErrorWrapper


@contextmanager
def wrap_error(name: Any, outer_type: type):
    try:
        yield
    except Exception as e:
        raise ValidationError([ErrorWrapper(e, (name,))], outer_type)


def validation_error(
    model: Any, error: Exception, location: Iterable[Union[int, str]]
) -> ValidationError:
    raise ValidationError(
        [
            ErrorWrapper(
                error,
                loc=tuple(location),
            )
        ],
        model,
    )
