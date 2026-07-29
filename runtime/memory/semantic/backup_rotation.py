import os
import glob
import shutil


class BackupRotation:


    def __init__(
        self,
        directory,
        keep=10
    ):
        self.directory=directory
        self.keep=keep



    def rotate(self):

        backups=sorted(
            glob.glob(
                os.path.join(
                    self.directory,
                    "*"
                )
            ),
            key=os.path.getmtime,
            reverse=True
        )


        for old in backups[self.keep:]:

            if os.path.isdir(old):
                shutil.rmtree(
                    old,
                    ignore_errors=True
                )
