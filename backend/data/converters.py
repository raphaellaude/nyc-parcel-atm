LAT_REGEX = r'^(\+|-)?(?:90(?:(?:\.0{1,6})?)|(?:[0-9]|[1-8][0-9])(?:(?:\.[0-9]{1,14})?))$'
LON_REGEX = r'^(\+|-)?(?:180(?:(?:\.0{1,6})?)|(?:[0-9]|[1-9][0-9]|1[0-7][0-9])(?:(?:\.[0-9]{1,14})?))$'
YEARS_REGEX = r"\b(?:0[1-9]|1\d|2[0-3])\b"

class LatConverter:
    regex = LAT_REGEX

    def to_python(self, value):
        print(value)
        return float(value)

    def to_url(self, value):
        print(value)
        return str(value)


class LonConverter:
    regex = LON_REGEX

    def to_python(self, value):
        print(value)
        return float(value)

    def to_url(self, value):
        print(value)
        return str(value)
