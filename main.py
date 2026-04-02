import os, time, json
from gdrive_api import GoogleDriveAPI
from meta_api import MetaAPI
def main():
            print("Bot Start")
            drive = GoogleDriveAPI()
            if not drive.service: return
                        try:
                                        with open("schedule_queue.json", "r") as f:
                                                            queue = json.load(f)
                                                    except:
        queue = []
    meta = MetaAPI()
    now = time.time()
    for item in queue:
                    if item.get('schedule_time', 0) <= now:
                                        for acc in item.get('accounts', []):
                                                                meta.post_reel(acc, item.get('gdrive_id'), item.get('caption'))
                                                    print("Bot End")
main()
