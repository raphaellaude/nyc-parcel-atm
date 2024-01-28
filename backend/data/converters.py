class LatConverter:
    regex = r'^-?(?:90(?:(?:\.0{1,3})?)|(?:[0-9]|[1-8][0-9])(?:(?:\.[0-9]{1,6})?))$'

    def to_python(self, value):
        print(value)
        return float(value)

    def to_url(self, value):
        print(value)
        return str(value)


class LonConverter:
    regex = r'^-?(?:180(?:(?:\.0{1,3})?)|(?:[0-9]|[1-9][0-9]|1[0-7][0-9])(?:(?:\.[0-9]{1,6})?))$'

    def to_python(self, value):
        print(value)
        return float(value)

    def to_url(self, value):
        print(value)
        return str(value)
