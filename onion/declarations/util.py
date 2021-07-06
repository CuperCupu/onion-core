from typing import Union, Iterable, Any

from pydantic import ValidationError
from pydantic.error_wrappers import ErrorWrapper


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
