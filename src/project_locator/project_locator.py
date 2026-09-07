
import sys, os

def get_project_location() -> str:
    main_file = sys.modules["__main__"].__file__
    path = os.path.dirname(os.path.abspath(main_file))
    return path