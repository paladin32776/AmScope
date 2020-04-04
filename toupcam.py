from numpy import zeros, uint8, uint32
import ctypes

TOUPCAM_EVENT_EXPOSURE = 1  # exposure time changed
TOUPCAM_EVENT_TEMPTINT = 2  # white balance changed
TOUPCAM_EVENT_CHROME = 3  # reversed, do not use it
TOUPCAM_EVENT_IMAGE = 4  # live image arrived, use Toupcam_PullImage to get this image
TOUPCAM_EVENT_STILLIMAGE = 5  # snap (still) frame arrived, use Toupcam_PullStillImage to get this frame
TOUPCAM_EVENT_ERROR = 80  # something error happens
TOUPCAM_EVENT_DISCONNECTED = 81  # camera disconnected

lib = ctypes.cdll.LoadLibrary('libtoupcam.dylib')


class HToupCam(ctypes.Structure):
    _fields_ = [('unused', ctypes.c_int)]


def success(r):
    return r == 0


class ToupCamCamera(object):

    _data = None
    _frame_fn = None
    _temptint_cb = None

    resolution_list = None
    resolution_number = None
    resolution = None

    def __init__(self, resolution_number=None, bits=32, resolution=None):

        self.cam = self.get_camera()

        self.resolution_list = self.get_resolution_list()
        if len(self.resolution_list) == 0:
            print("No valid resolutions found\n")
            return

        if resolution_number is None and resolution is None:
            resolution_number = 0

        if resolution_number is not None:
            if resolution_number not in range(len(self.resolution_list)):
                raise ValueError('Resolution number not supported')
            self.resolution_number = resolution_number
        elif resolution is not None:
            if resolution not in self.resolution_list:
                raise ValueError('Resolution not supported')
            self.resolution_number = self.resolution_list.index(resolution)

        self.resolution = self.resolution_list[self.resolution_number]

        if bits not in (32,):
            raise ValueError('Bits needs to by 8 or 32')

        self.bits = bits

    # icamera interface
    def get_cv2_image(self):
        data = self._data
        raw = data.view(uint8).reshape(data.shape + (-1,))
        bgr = raw[..., :3]

        return bgr

    def get_image_data(self):
        d = self._data
        return d

    def close(self):
        if self.cam:
            lib.Toupcam_Close(self.cam)

    def open(self):

        self.set_resolution_number(self.resolution_number)

        args = self.get_resolution()
        if not args:
            return

        h, w = args[1], args[0]

        shape = (h, w)
        if self.bits == 8:
            dtype = uint8
        else:
            dtype = uint32

        self._data = zeros(shape, dtype=dtype)

        bits = ctypes.c_int(self.bits)

        def get_frame(n_event, ctx):
            if n_event == TOUPCAM_EVENT_IMAGE:
                w_pull, h_pull = ctypes.c_uint(), ctypes.c_uint()

                lib.Toupcam_PullImage(self.cam, ctypes.c_void_p(self._data.ctypes.data), bits,
                                      ctypes.byref(w_pull),
                                      ctypes.byref(h_pull))

        callback = ctypes.CFUNCTYPE(None, ctypes.c_uint, ctypes.c_void_p)
        self._frame_fn = callback(get_frame)

        result = lib.Toupcam_StartPullModeWithCallback(self.cam, self._frame_fn)

        return success(result)

    # ToupCam interface
    def _lib_func(self, func, *args, **kw):
        ff = getattr(lib, 'Toupcam_{}'.format(func))
        result = ff(self.cam, *args, **kw)
        return success(result)

    def _lib_get_func(self, func):
        v = ctypes.c_int()
        if self._lib_func('get_{}'.format(func), ctypes.byref(v)):
            return v.value

    # setters
    def set_gamma(self, v):
        self._lib_func('put_Gamma', ctypes.c_int(v))

    def set_contrast(self, v):
        self._lib_func('put_Contrast', ctypes.c_int(v))

    def set_brightness(self, v):
        self._lib_func('put_Brightness', ctypes.c_int(v))

    def set_saturation(self, v):
        self._lib_func('put_Saturation', ctypes.c_int(v))

    def set_hue(self, v):
        self._lib_func('put_Hue', ctypes.c_int(v))

    def set_exposure_time(self, v):
        self._lib_func('put_ExpoTime', ctypes.c_ulong(v))

    # getters
    def get_gamma(self):
        return self._lib_get_func('Gamma')

    def get_contrast(self):
        return self._lib_get_func('Contrast')

    def get_brightness(self):
        return self._lib_get_func('Brightness')

    def get_saturation(self):
        return self._lib_get_func('Saturation')

    def get_hue(self):
        return self._lib_get_func('Hue')

    def get_exposure_time(self):
        return self._lib_get_func('ExpoTime')

    def do_awb(self, callback=None):
        """
        Toupcam_AwbOnePush(HToupCam h, PITOUPCAM_TEMPTINT_CALLBACK fnTTProc, void* pTTCtx);
        :return:
        """

        def temptint_cb(temp, tint):
            if callback:
                callback((temp, tint))

        callback = ctypes.CFUNCTYPE(None, ctypes.c_uint, ctypes.c_void_p)
        self._temptint_cb = callback(temptint_cb)

        return self._lib_func('AwbOnePush', self._temptint_cb)

    def set_temperature_tint(self, temp, tint):
        lib.Toupcam_put_TempTint(self.cam, temp, tint)

    def get_temperature_tint(self):
        temp = ctypes.c_int()
        tint = ctypes.c_int()
        if self._lib_func('get_TempTint', ctypes.byref(temp), ctypes.byref(tint)):
            return temp.value, tint.value

    def get_auto_exposure(self):
        expo_enabled = ctypes.c_bool()
        result = lib.Toupcam_get_AutoExpoEnable(self.cam, ctypes.byref(expo_enabled))
        if success(result):
            return expo_enabled.value

    def set_auto_exposure(self, expo_enabled):
        lib.Toupcam_put_AutoExpoEnable(self.cam, expo_enabled)

    def get_camera(self, cid=None):
        func = lib.Toupcam_Open
        func.restype = ctypes.POINTER(HToupCam)
        cam = func(cid)
        return cam

    def get_serial(self):
        sn = ctypes.create_string_buffer(32)
        result = lib.Toupcam_get_SerialNumber(self.cam, sn)
        if success(result):
            sn = sn.value
            return sn

    def get_firmware_version(self):
        fw = ctypes.create_string_buffer(16)
        result = lib.Toupcam_get_FwVersion(self.cam, fw)
        if success(result):
            return fw.value

    def get_hardware_version(self):
        hw = ctypes.create_string_buffer(16)
        result = lib.Toupcam_get_HwVersion(self.cam, hw)
        if success(result):
            return hw.value

    def get_resolution(self):
        w, h = ctypes.c_long(), ctypes.c_long()

        result = lib.Toupcam_get_Size(self.cam, ctypes.byref(w), ctypes.byref(h))
        if success(result):
            return w.value, h.value

    def get_resolution_number(self):
        res = ctypes.c_long()
        result = lib.Toupcam_get_eSize(self.cam, ctypes.byref(res))
        if success(result):
            return res.value

    def set_resolution_number(self, nres):
        lib.Toupcam_put_eSize(self.cam, ctypes.c_ulong(nres))

    def set_resolution(self, w, h):
        self._lib_func('put_Size', ctypes.c_long(w), ctypes.c_long(h))

    def get_resolution_list(self):
        nmax = lib.Toupcam_get_ResolutionNumber(self.cam)
        res_list = []
        for n in range(nmax):
            w, h = ctypes.c_long(), ctypes.c_long()
            result = lib.Toupcam_get_Resolution(self.cam, ctypes.c_int(n), ctypes.byref(w), ctypes.byref(h))
            if success(result):
                res_list = res_list + [[w.value, h.value]]
        return res_list
