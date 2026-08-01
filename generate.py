def parse_topic_file(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "|" not in line:
                continue
            en, ko = line.split("|", 1)
            rows.append((en.strip(), ko.strip()))
    return rows
