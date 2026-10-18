#!/usr/bin/env python3
"""
Radio Betel – publicarea unei înregistrări pe un canal (muzica / predici).

Pași făcuți automat:
  1. decupează (opțional) intervalul dorit din înregistrarea serviciului (ex. doar predica);
  2. convertește la MP3, cu volum normalizat (predici: mono 64 kbps; muzică: stereo 128 kbps);
  3. urcă fișierul pe Internet Archive (archive.org – găzduire gratuită, fără limită de trafic);
  4. adaugă piesa în playlistul canalului (radio/muzica.json sau radio/predici.json).

Sursa: înregistrările de pe canalul bisericii, descărcate din YouTube Studio
(Conținut → ⋮ lângă videoclip → Descarcă). Folosiți doar materiale pentru care biserica are drepturile.

Instalare (o singură dată, pe calculatorul care publică):
  - ffmpeg:            https://ffmpeg.org/download.html  (Windows: winget install ffmpeg)
  - Python 3.9+:       pip install internetarchive
  - cont archive.org:  ia configure   (cere emailul și parola contului Internet Archive)

Exemple:
  python publica.py predici "Serviciu 11 oct.mp4" --titlu "Credința care biruiește" --autor "Pastor Ion Popescu" \
         --data 2026-10-11 --de 1:05:30 --pana 1:52:10 --sursa https://youtu.be/XXXXXXXXXXX
  python publica.py muzica "Laudă - Doamne, Tu ești.mp3" --titlu "Doamne, Tu ești" --autor "Grupul de laudă Betel" \
         --autori "Text și muzică: Grupul de laudă Betel"
  python publica.py muzica "Mare esti Tu.wav" --titlu "Mare ești Tu" --autor "Tineretul Betel" --cover \
         --autori "Chris Tomlin, Jesse Reeves, Ed Cash" --traducere "Daniel Ionescu" --original "How Great Is Our God (Chris Tomlin)"
  python publica.py predici fisier.mp4 --titlu "Test" --doar-local     (fără urcare: verifică doar conversia)

După rulare: încărcați pe GitHub fișierul JSON modificat (sau folosiți --push dacă folderul e o clonă git).
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

CANALE = {
    'muzica': {'json': 'muzica.json', 'audio': ['-ac', '2', '-b:a', '128k'], 'nume': 'Muzică'},
    'predici': {'json': 'predici.json', 'audio': ['-ac', '1', '-b:a', '64k'], 'nume': 'Predici'},
}
RADIO_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def fail(msg):
    print('EROARE: ' + msg, file=sys.stderr)
    sys.exit(1)


def slug(s, n=48):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = re.sub(r'[^A-Za-z0-9]+', '-', s).strip('-').lower()
    return s[:n].strip('-') or 'inregistrare'


def timp(v):
    """'1:05:30', '65:30' sau '3930' → secunde."""
    if v is None:
        return None
    parts = v.strip().split(':')
    if not all(re.fullmatch(r'\d+(\.\d+)?', p) for p in parts) or len(parts) > 3:
        fail('Timp invalid: %r (folosiți hh:mm:ss, mm:ss sau secunde).' % v)
    sec = 0.0
    for p in parts:
        sec = sec * 60 + float(p)
    return sec


def durata(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', path],
                         capture_output=True, text=True)
    try:
        return round(float(out.stdout.strip()), 1)
    except ValueError:
        fail('Nu pot citi durata fișierului %s.' % path)


def converteste(src, dst, canal, de, pana):
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y']
    if de is not None:
        cmd += ['-ss', str(de)]
    cmd += ['-i', src]
    if pana is not None:
        cmd += ['-t', str(pana - (de or 0))]
    # loudnorm: volum egal între piese (−16 LUFS, standardul pentru ascultare online)
    cmd += ['-vn', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-ar', '44100', '-codec:a', 'libmp3lame'] + CANALE[canal]['audio'] + [dst]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        fail('Conversia a eșuat:\n' + r.stderr[-2000:])


def urca(path, identifier, a):
    try:
        import internetarchive as ia
    except ImportError:
        fail('Lipsește pachetul internetarchive: pip install internetarchive, apoi ia configure.')
    credite = '\n'.join(x for x in [
        ('Cover (interpretare a Bisericii Betel Constanța)' if a.cover else ''),
        ('Autori: ' + a.autori if a.autori else ''),
        ('Traducerea: ' + a.traducere if a.traducere else ''),
        ('Original: ' + a.original if a.original else '')] if x)
    meta = {
        'mediatype': 'audio',
        'collection': 'opensource_audio',
        'title': a.titlu,
        'creator': a.autor or 'Biserica Betel Constanța',
        'date': a.data or dt.date.today().isoformat(),
        'language': 'rum',
        'subject': ['Biserica Betel Constanța', 'Radio Betel', CANALE[a.canal]['nume']] + (['cover'] if a.cover else []),
        'description': '\n'.join(x for x in [a.descriere, credite, ('Sursa: ' + a.sursa if a.sursa else '')] if x),
    }
    name = os.path.basename(path)
    print('Urc pe archive.org: %s …' % identifier)
    r = ia.upload(identifier, files={name: path}, metadata=meta, retries=5, retries_sleep=20, verbose=True)
    if not r or any(getattr(x, 'status_code', 200) >= 400 for x in r):
        fail('Urcarea pe archive.org a eșuat.')
    return 'https://archive.org/download/%s/%s' % (identifier, name)


def main():
    p = argparse.ArgumentParser(description='Publică o înregistrare pe Radio Betel.')
    p.add_argument('canal', choices=sorted(CANALE))
    p.add_argument('fisier', help='înregistrarea (mp4, m4a, mp3, wav …)')
    p.add_argument('--titlu', required=True)
    p.add_argument('--autor', default='', help='predicatorul / cine cântă (ex. Grupul de laudă Betel)')
    p.add_argument('--autori', default='', help='muzică: autorii cântării (text și muzică); obligatoriu la muzică ("Tradițional" dacă nu se știu)')
    p.add_argument('--cover', action='store_true', help='muzică: cântarea altor autori, interpretată de biserică')
    p.add_argument('--traducere', default='', help='muzică: autorul traducerii în română')
    p.add_argument('--original', default='', help='muzică: versiunea originală (titlu, interpret)')
    p.add_argument('--data', default='', help='AAAA-LL-ZZ (data predicii)')
    p.add_argument('--de', help='începutul fragmentului (hh:mm:ss)')
    p.add_argument('--pana', help='sfârșitul fragmentului (hh:mm:ss)')
    p.add_argument('--sursa', default='', help='linkul videoclipului de pe YouTube (opțional)')
    p.add_argument('--descriere', default='')
    p.add_argument('--doar-local', action='store_true', help='nu urcă nimic: păstrează MP3-ul lângă fișierul sursă')
    p.add_argument('--push', action='store_true', help='face commit + push în depozitul git al paginii')
    a = p.parse_args()

    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        fail('Lipsește ffmpeg (ffmpeg și ffprobe trebuie să fie în PATH).')
    if not os.path.isfile(a.fisier):
        fail('Nu găsesc fișierul %s.' % a.fisier)
    if a.data and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', a.data):
        fail('Data trebuie scrisă AAAA-LL-ZZ (ex. 2026-10-11).')
    if a.sursa and not a.sursa.startswith('https://'):
        fail('Linkul sursei trebuie să înceapă cu https://')
    for k in ('titlu', 'autor', 'autori', 'traducere', 'original'):
        setattr(a, k, ' '.join(getattr(a, k).split()))
    if a.canal == 'muzica' and not a.autori:
        fail('La muzică, scrieți autorii cântării cu --autori (text și muzică; "Tradițional" dacă nu se știu). '
             'Mențiunea autorilor este obligatorie, chiar și la cântările interpretate de biserică.')
    if a.canal != 'muzica' and (a.cover or a.autori or a.traducere or a.original):
        fail('--cover, --autori, --traducere și --original sunt doar pentru canalul muzica.')
    de, pana = timp(a.de), timp(a.pana)
    if de is not None and pana is not None and pana <= de:
        fail('--pana trebuie să fie după --de.')

    zi = a.data or dt.date.today().isoformat()
    base = '%s-%s' % (zi, slug(a.titlu))
    identifier = 'radio-betel-%s-%s' % (a.canal, base)
    tmp = tempfile.mkdtemp(prefix='radio-betel-')
    mp3 = os.path.join(tmp, base + '.mp3')
    print('Convertesc „%s” …' % a.fisier)
    converteste(a.fisier, mp3, a.canal, de, pana)
    sec = durata(mp3)
    print('Gata: %s (%d min %02d s, %.1f MB)' % (os.path.basename(mp3), sec // 60, sec % 60, os.path.getsize(mp3) / 1e6))

    if a.doar_local:
        out = os.path.join(os.path.dirname(os.path.abspath(a.fisier)), base + '.mp3')
        shutil.move(mp3, out)
        print('Fișierul a rămas local: %s (playlistul nu a fost modificat).' % out)
        return
    url = urca(mp3, identifier, a)
    shutil.rmtree(tmp, ignore_errors=True)

    jpath = os.path.join(RADIO_DIR, CANALE[a.canal]['json'])
    with open(jpath, encoding='utf-8') as f:
        pl = json.load(f)
    pl.setdefault('piese', [])
    if any(x.get('url') == url for x in pl['piese']):
        print('Piesa era deja în playlist.')
    else:
        item = {'titlu': a.titlu, 'autor': a.autor, 'data': a.data, 'url': url, 'durata': sec}
        if a.sursa:
            item['sursa'] = a.sursa
        if a.canal == 'muzica':
            item['autori'] = a.autori
            if a.cover:
                item['cover'] = True
            if a.traducere:
                item['traducere'] = a.traducere
            if a.original:
                item['original'] = a.original
        pl['piese'].append(item)
        with open(jpath, 'w', encoding='utf-8') as f:
            json.dump(pl, f, ensure_ascii=False, indent=2)
            f.write('\n')
        print('Adăugată în %s (%d piese).' % (CANALE[a.canal]['json'], len(pl['piese'])))
    print('Link: ' + url)
    if a.push:
        repo = os.path.dirname(RADIO_DIR)
        subprocess.run(['git', '-C', repo, 'add', jpath], check=True)
        subprocess.run(['git', '-C', repo, 'commit', '-m', 'Radio Betel: ' + a.titlu], check=True)
        subprocess.run(['git', '-C', repo, 'push'], check=True)
        print('Publicat pe GitHub. Apare în radio în 1–2 minute.')
    else:
        print('Acum încărcați pe GitHub fișierul %s (Upload files / editare) ca piesa să apară în radio.' % CANALE[a.canal]['json'])


if __name__ == '__main__':
    main()
