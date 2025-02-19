import argparse
import hashlib
import shutil
import time
from pathlib import Path
import logging

def setup_logger(log_file, level):

    logger = logging.getLogger("ReplicatorLogger")
    logger.setLevel(level)

    log_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(log_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

def copy_item(path, item_to_copy):
    destination = path / item_to_copy.name
    if item_to_copy.is_file():
        shutil.copy2(item_to_copy, destination)
    elif item_to_copy.is_dir():
        shutil.copytree(item_to_copy, destination)
        
def get_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()    

def recursive_replicate_folder(source_path, replica_path, logger):

    if not replica_path.exists():
        logger.warning(f"Replica folder '{replica_path}' does not exist. Creating it.")
        replica_path.mkdir(parents=True, exist_ok=True)
    
    replica_names = [file.name for file in replica_path.iterdir()]
    source_items = [file for file in source_path.iterdir()]

    for item in source_items:
        item_replica_path = replica_path / item.name
        if item.name not in replica_names:
            copy_item(replica_path, item)
            if item.is_dir():
                logger.info(f"Folder created: {item_replica_path}")
                for child_item in item_replica_path.rglob('*'):
                    if child_item.is_file():
                        logger.info(f"File created: {child_item}")
                    else:
                        logger.info(f"Folder created: {child_item}")
            elif item.is_file():
                logger.info(f"File created: {item_replica_path}")

        elif item.is_file():
            if (item.stat().st_size != item_replica_path.stat().st_size or
                item.stat().st_mtime != item_replica_path.stat().st_mtime or
                get_md5(item) != get_md5(item_replica_path)):
                copy_item(replica_path, item)
                logger.info(f"File copied: {item_replica_path}")
            replica_names.remove(item.name)
        else:
            recursive_replicate_folder(item, item_replica_path, logger)
            replica_names.remove(item.name)
    
    for extra_item in replica_names:
        item_path =  (replica_path / extra_item)
        if item_path.is_file():
            item_path.unlink(missing_ok=True)
            logger.info(f"File removed: {item_path}")
        else:
            logger.info(f"Folder removed: {item_path}")
            shutil.rmtree(item_path)

def main():

    parser = argparse.ArgumentParser(description="File replicator script.")
    parser.add_argument("--source", type=str, help="Source folder path")
    parser.add_argument("--replica", type=str, help="Replica folder path")
    parser.add_argument("--interval", type=int, help="Sync interval in seconds")
    parser.add_argument("--log_path", type=str, help="Log file path")
    args = parser.parse_args()
    
    logger = setup_logger(args.log_path, logging.INFO)  

    source_folder_path = Path(args.source)
    replica_folder_path = Path(args.replica)

    if not source_folder_path.exists():
        logger.error(f"Source folder '{source_folder_path}' does not exist.")
        return

    try:
        while True:
            recursive_replicate_folder(source_folder_path, replica_folder_path, logger)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("Synchronization stopped by user.")
    
if __name__ == "__main__":
    main()
