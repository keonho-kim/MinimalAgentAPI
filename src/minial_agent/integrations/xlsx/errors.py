class XlsxEngineError(ValueError):
    """Base error for XLSX engine failures."""


class XlsxRangeError(XlsxEngineError):
    """Raised when a sheet, cell, or range reference is invalid."""


class XlsxSessionError(XlsxEngineError):
    """Raised when an XLSX session cannot be loaded or used."""


class XlsxTransformError(XlsxEngineError):
    """Raised when a dataframe transform is invalid or fails."""
