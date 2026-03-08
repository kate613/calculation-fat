from ultralytics import YOLO

MODEL_PATH = 'yolov8n.pt'

CLASS_MAP = {
    'apple':          'apple',
    'banana':         'banana',
    'orange':         'orange',
    'carrot':         'carrot',
    'broccoli':       'carrot',
    'sandwich':       'bread',
    'pizza':          'bread',
    'bread':          'bread',
    'hot dog':        'beef',
    'chicken':        'chicken',
    'rice':           'rice',
    'pasta':          'pasta',
    'beef':           'beef',
    'steak':          'beef',
    'hamburger':      'beef',
    'fish':           'fish',
    'salmon':         'fish',
    'egg':            'egg',
    'milk':           'milk',
    'cheese':         'cheese',
    'tomato':         'tomato',
    'potato':         'potato',
    'french fries':   'potato',
}

_model = None


def get_model():
    global _model
    if _model is None:
        _model = YOLO(MODEL_PATH)
    return _model


def recognize(image_path):
    model = get_model()
    results = model.predict(image_path, verbose=False)
    best_name = None
    best_conf = 0.0
    for result in results:
        for box in result.boxes:
            class_name = result.names[int(box.cls[0])].lower()
            confidence = float(box.conf[0])
            mapped = CLASS_MAP.get(class_name)
            if mapped and confidence > 0.4 and confidence > best_conf:
                best_name = mapped
                best_conf = confidence
    return best_name
