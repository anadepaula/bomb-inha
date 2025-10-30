import configparser


config = configparser.ConfigParser()
config.read("config.ini") 

ENCODED_FILE_PATH = config["INPUT FILES"]["encoded_file_path"]  
QUADGRAMS_FREQUENCY_FILE_PATH = config["INPUT FILES"]["quadgrams_frequency_file_path"]  

ZERO = config["CONSTANTS"]["zero"]  
ONE = config["CONSTANTS"]["one"]
