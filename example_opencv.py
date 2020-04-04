import cv2
import time
from toupcam import ToupCamCamera
import matplotlib.pyplot as plt

cam = ToupCamCamera(resolution_number=1)
cam.open()
cam.set_auto_exposure(0)
cam.set_exposure_time(50000)


cv2.namedWindow('image', cv2.WINDOW_NORMAL)
while (True):
    im = cam.get_cv2_image()
    im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    # im2 = im
    # im2[:,:,0] = im[:,:,2]
    # im2[:, :, 2] = im[:, :, 0]
    cv2.imshow('image', im)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cv2.destroyAllWindows()

# time.sleep(0.20)
# im = cam.get_cv2_image()
# plt.imshow(im)


cam.close()