import os

IMAGE_DIR = "/Users/tomov90/Pictures"
#IMAGE_DIR = "/Users/tomov90/Movies"
VIDEO_EXTS = ['3gp', 'avi', 'mov', 'mpg', 'mpeg', 'mp4', 'flv', 'mts', 'wmv', 'm4v']
IMAGE_EXTS = ['jpeg', 'jpg', 'png', 'gif', 'bmp']

TARGET_DIR = "/Users/tomov90/Pictures/VIDEOS"

created_dirs = dict()

def crawl():
    start_path = IMAGE_DIR 
    foo = os.walk(start_path)
    for data in foo:
        (dirpath, dirnames, filenames) = data
        for f in filenames :
            ext = f.lower().split(".")[-1]
            fullpath = dirpath + "/" + f
            if not dirpath[:len(TARGET_DIR)] == TARGET_DIR and ext in VIDEO_EXTS:
                relpath = fullpath[len(start_path):]
                
                reldir = dirpath[len(start_path):]
                dirname = reldir[1:].replace("/", " -- ")
                print fullpath

                target = TARGET_DIR + "/" + dirname + "/" + f
                print "      ----> " + target

                os.rename(fullpath, target)
                #if not dirname in created_dirs:
                #    created_dirs[dirname] = 1

                #    newdir = TARGET_DIR + "/" + dirname
                    #os.mkdir(newdir)
                #    print "                           NEW DIR!"



if __name__ == "__main__":
    crawl()
