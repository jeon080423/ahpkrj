import codecs

path = 'n:/개인/M 연구1부 공유폴더/1. 제안서 작업(2026)/(수주) 22.서울시복지재단_2026년 서울시노인실태조사/4. 최종제출/제안발표_original.txt'
out_path = 'g:/AHPkr/temp_utf8.txt'

for enc in ['utf-8', 'utf-16', 'utf-16le', 'utf-16be', 'cp949']:
    try:
        with open(path, 'r', encoding=enc) as f:
            content = f.read()
        print(f"Success with {enc}")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(content)
        break
    except Exception as e:
        pass
