BAD_COOKIE_KEYS = {
    'expiry',
    'sameSite',
    'httpOnly'
}  # These cookies are not compatible with the requests.Response interface

CAPTCHA_STRS = {
    'Please show you\'re not a robot',
    'verify you\'re not a robot',
    'Please show you&#39;re not a robot'
}