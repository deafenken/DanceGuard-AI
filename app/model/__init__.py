from importlib import import_module

__all__ = [
    "DanceSet",
    "BvhDatasetBuilder",
    "build_bvh_training_data",
    "fake_data",
    "EvalNet",
    "train_epoch",
    "load_model",
    "predict",
    "Scorer",
    "VmcReceiver",
    "MocapRecorder",
]

_MODULE_MAP = {
    "DanceSet": (".data", "DanceSet"),
    "BvhDatasetBuilder": (".data", "BvhDatasetBuilder"),
    "build_bvh_training_data": (".data", "build_bvh_training_data"),
    "fake_data": (".data", "fake_data"),
    "EvalNet": (".net", "EvalNet"),
    "train_epoch": (".train", "train_epoch"),
    "load_model": (".infer", "load_model"),
    "predict": (".infer", "predict"),
    "Scorer": (".runtime", "Scorer"),
    "VmcReceiver": (".vmc", "VmcReceiver"),
    "MocapRecorder": (".vmc", "MocapRecorder"),
}


def __getattr__(name):
    if name not in _MODULE_MAP:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _MODULE_MAP[name]
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
