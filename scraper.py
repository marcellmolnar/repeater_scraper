import csv
from dotenv import load_dotenv
import os
import requests
from bs4 import BeautifulSoup
from unidecode import unidecode

new_headers = {
    "Location": None, "Name": "QTH/Név", "Frequency": "Lejövő[kHz]", "Duplex":None, "Offset":"Elt.[kHz]", "Tone":None, "rToneFreq":None, "cToneFreq":None, "DtcsCode":None, "DtcsPolarity":None, "RxDtcsCode":None, "CrossMode":None, "Mode":"Üzemmód", "TStep":None, "Skip":None, "Power":None, "Comment":None, "URCALL":None, "RPT1CALL":None, "RPT2CALL":None, "DVCODE":None}

def create_from(id: int, name: str, freq: str, comment: str):
    return [str(id), name, freq, '-', '0', '', '88.5', '88.5', '023', 'NN', '023', 'Tone->Tone', 'FM', '12.5', '', '1.0W', comment, '', '', '', '']

# Location,Name,Frequency,Duplex,Offset,Tone,rToneFreq,cToneFreq,DtcsCode,DtcsPolarity,RxDtcsCode,CrossMode,Mode,TStep,Skip,Power,Comment,URCALL,RPT1CALL,RPT2CALL,DVCODE
fix_stations = [
    create_from(0, 'BUD REPTER', '118.1000', 'BUD REPTER, BUDAPESTI REPÜLŐTÉR'),
    create_from(1, 'BALATON NY', '161.7000', 'BALATON INFO NYUGAT'),
    create_from(2, 'BALATON K', '161.6000', 'BALATON INFO KELET'),
    create_from(3, 'VHF HIVO', '145.5000', 'VHF (2m) HIVO'),
    create_from(4, 'UHF HIVO', '433.5000', 'UHF (70cm) HIVO')
]

def fix_station_name(nameOrig, maxLen=10):
    name = nameOrig.upper().replace('BUDAPEST', 'BP').replace('(', '').replace(')', '')
    # replace special characters
    name = unidecode(name)
    return name[:maxLen] if len(name) > maxLen else name

def convert_table(csv_writer, loc, table, isDMR):
    print(f"{"normal" if not isDMR else "DMR"} table:")

    rows = table.find_all('tr')
    if not rows:
        print("No rows found in the table.")
        return
    print(f"Found {len(rows)} rows in the table.")

    rc = 0
    headerNames = []
    for row in rows:
        cells = row.find_all('td' if rc > 0 else 'th')
        #assert cells is None, f"No cells found in the row {rc}"
        data = [cell.get_text(strip=True) for cell in cells]
        if rc == 0:
            headerNames = data
            print(f"Header names: {headerNames}")
            rc += 1
            continue

        if 'aktív' != data[headerNames.index('Állapot')]:
            continue

        if rc < 5:
            print(data)  # Print or process the data as needed

        new_line = []
        col = 0
        for colName, oldName in new_headers.items():
            if colName == "Location":
                new_line.append(loc + rc - 1)
            elif colName == "Name":
                nameS = fix_station_name(data[headerNames.index(oldName)])
                new_line.append(nameS)
            elif colName == "Frequency":
                f = float(data[headerNames.index(oldName)]) / 1000
                new_line.append(f)
            elif colName == "Duplex":
                new_line.append('-')
            elif colName == "Offset":
                d = data[headerNames.index(oldName)]
                if d is None or d == '' or d == '-' or d == 'N/A':
                    o = 0
                else:
                    o = int(d)/1000
                # for some reason...
                o = -o
                new_line.append(o)
            elif colName == "Tone":
                new_line.append('TSQL')
            elif colName == "rToneFreq" or colName == "cToneFreq":
                if not isDMR:
                    d = data[headerNames.index('CTCSSDL/UL [Hz]')]
                    split = d.split('/')
                    def corr_freq(freq):
                        if freq == 'N/A' or freq == '' or freq == '-' or freq == '--':
                            return '88.5'
                        return freq
                    if colName == "rToneFreq":
                        new_line.append(corr_freq(split[0] if len(split) > 0 else '88.5'))
                    else:
                        new_line.append(corr_freq(split[1] if len(split) > 1 else '88.5'))
                else:
                    new_line.append('88.5')
            elif colName == "DtcsCode":
                new_line.append('023')
            elif colName == "DtcsPolarity":
                new_line.append('NN')
            elif colName == "RxDtcsCode":
                new_line.append('023')
            elif colName == "CrossMode":
                new_line.append('Tone->Tone')
            elif colName == "Mode":
                new_line.append('DMR' if isDMR else ('FM' if 'FM' in data[headerNames.index(oldName)] else 'DN'))
            elif colName == "TStep":
                new_line.append('12.5')
            elif colName == "Skip":
                new_line.append('')
            elif colName == "Power":
                new_line.append('1.0W')
            elif colName == "Comment":
                c = data[headerNames.index('Hívójel')] + " " + data[headerNames.index('QTH/Név')] + ", QTH: " + data[headerNames.index('QTH Lokátor')]
                new_line.append(c)
            elif colName in ['URCALL', 'RPT1CALL', 'RPT2CALL', 'DVCODE']:
                new_line.append('')

        csv_writer.writerow(new_line)
        rc += 1

    return loc + rc - 1 # -1 beacause of header

def main(refresh=False):
    if refresh:
        siteUrl = os.getenv("WEBPAGE")
        print("Starting web scraping...")
        print(f"Fetching data from {siteUrl}")
        try:
            response = requests.get(siteUrl)
            response.raise_for_status()  # Check for HTTP errors
        except requests.RequestException as e:
            print(f"Error fetching data: {e}")
            return

        data = response.content

        # serialize the response content
        with open('response.html', 'wb') as file:
            file.write(data)

    # read the response content from file
    with open('response.html', 'rb') as file:
        data = file.read()

    print("Data fetched successfully. Parsing HTML...")
    soup = BeautifulSoup(data, 'html.parser')

    tables = soup.find_all('table')
    if not tables:
        print("No table found in the HTML.")
        return
    else:
        print("Tables found. Extracting data...")

    with open('output.csv', 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=',')

        header = [k for k,_ in new_headers.items()]
        csv_writer.writerow(header)

        for s in fix_stations:
            csv_writer.writerow(s)

        putDMR = False
        i = 0
        rows = len(fix_stations)
        for table in tables:
            if i == 2 or (i == 1 and not putDMR):
                break
            rows = convert_table(csv_writer, rows, table, i == 1)
            print(" ")
            print(" ")
            i += 1

        csv_writer.writerow(create_from(rows, f"K", "147.1000", f"K"))
        rows += 1
    
        f = 145.2
        c = 0
        while f <= 145.575:
            csv_writer.writerow(create_from(rows, f"VHF {c}", f"{f:.4f}", f"VHF (2m) {f:.4f}"))
            f += 0.025
            rows += 1
            c += 1

        f = 433.0
        c = 0
        while f <= 434.575:
            csv_writer.writerow(create_from(rows, f"UHF {c}", f"{f:.4f}", f"UHF (70cm) {f:.4f}"))
            f += 0.025
            rows += 1
            c += 1

        f = 446.00625
        c = 1
        while f <= 446.19375:
            csv_writer.writerow(create_from(rows, f"PMR {c}", f"{f:.4f}", f"PMR {c} {f:.4f}"))
            f += 0.0125
            rows += 1
            c += 1


if __name__ == "__main__":
    load_dotenv()
    print(os.getenv("WEBPAGE"))

    main()
