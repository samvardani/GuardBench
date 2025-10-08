import sys as _sys
# Import score_pb2 first, then alias, then import score_pb2_grpc (which imports score_pb2)
from . import score_pb2 as _score_pb2  # type: ignore
_sys.modules.setdefault("score_pb2", _score_pb2)
from . import score_pb2_grpc as _score_pb2_grpc  # type: ignore
_sys.modules.setdefault("score_pb2_grpc", _score_pb2_grpc)

__all__ = ["score_pb2", "score_pb2_grpc"]


