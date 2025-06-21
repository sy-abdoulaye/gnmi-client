import logging
import argparse
from yaml import load as yaml_load
from yaml import Loader as yaml_loader
from yaml import full_load as yaml_full_load

class GetLogger(logging.Filter):
    def __init__(self):
        super().__init__()
    
    @staticmethod
    def setup_logging():
        """
        Configure and return a logger
        """
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(name)s-%(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            force=True
        )

        logger = logging.getLogger()
        
        return logger

def parse_args(dynamic_args=None, parser=argparse.ArgumentParser().parse_known_args, return_kwargs=False):
    if not dynamic_args:
        _, dynamic_args = parser()
    
    kwargs = {}
    for arg in dynamic_args:
        if arg[0] == '-':
            if return_kwargs:
                arg = arg[1:]
                if arg[0] == '-':
                    arg = arg[1:]
                arg = arg.replace('-', '_')
            key = arg
            kwargs.update({
                key: None
            })
            continue
        if kwargs[key]:
            kwargs[key] = f"{kwargs[key]} {arg}"
        else:
            kwargs[key] = arg
     
    return kwargs
    
def load_data(file_extension:str, file_path:str, full_load=True):
    """
    Load data from a file of a given extension. 
    """
    loaded_data = None
    with open(file_path) as f:
        if file_extension == "yaml":
            if full_load:
                loaded_data = yaml_full_load(f)
            else:
                loaded_data = yaml_load(
                    f,
                    Loader=yaml_loader
                )
        return loaded_data