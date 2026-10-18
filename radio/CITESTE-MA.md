# Radio Betel: două canale (Muzică și Predici), cost zero

## Cum funcționează
- **Pagina radioului** (`radio/index.html`) este statică. Stă în același depozit GitHub Pages ca pagina-ramă a Caietului: `https://<utilizator>.github.io/caiet/radio/`.
- **Fișierele audio (MP3)** sunt găzduite gratuit pe **Internet Archive** (archive.org), fără limită de trafic și fără legătură cu Google Drive sau cu foile de calcul ale aplicației.
- **Playlisturile** sunt două fișiere text: `radio/muzica.json` și `radio/predici.json`. Le modifică scriptul de publicare sau le poți edita direct pe GitHub.
- **„Radioul”:** poziția de redare se calculează din ceas. Toți ascultătorii aud aceeași piesă în același moment, ca la un post de radio, fără server de streaming.
- **La Predici** există și o **arhivă**: oricine poate asculta o predică de la început, apoi apasă „Revino la radio”.
- **Pe telefon** sunetul merge cu ecranul blocat. Comenzile de pe ecranul de blocare afișează titlul și sigla.

## Instalare (o singură dată)
1. Copiază folderul `radio/` în depozitul GitHub al pagini-ramă, lângă `index.html` (Add file → Upload files). Iconițele ramei sunt folosite și de radio.
2. În `muzica.json` și `predici.json`, înlocuiește `"youtube"` cu adresa canalului bisericii. Lasă `"start"` neschimbat: e momentul de pornire al radioului.
3. Creează un cont gratuit pe https://archive.org (Sign up).
4. Pe calculatorul care publică:
   - instalează **ffmpeg** (Windows: `winget install ffmpeg`) și **Python 3**;
   - rulează `pip install internetarchive`;
   - rulează `ia configure` (cere emailul și parola contului archive.org).

## Publicarea unei predici (aproximativ 5 minute)
1. În **YouTube Studio**, mergi la Conținut. La serviciul dorit, apasă ⋮ → **Descarcă**. Proprietarul canalului are voie să descarce astfel propriile videoclipuri.
2. Notează minutul de început și de sfârșit al predicii.
3. Rulează:
   ```
   python radio/unelte/publica.py predici "Serviciu 11 oct.mp4" --titlu "Credința care biruiește" ^
          --autor "Pastor Ion Popescu" --data 2026-10-11 --de 1:05:30 --pana 1:52:10 --sursa https://youtu.be/XXXXXXXXXXX
   ```
   Pe macOS/Linux, înlocuiește `^` cu `\`.

   Scriptul face trei lucruri:
   - decupează predica;
   - o convertește în MP3 mono la 64 kbps, cu volum egalizat (aproximativ 22 MB pe oră);
   - o urcă pe archive.org și o adaugă în `predici.json`.
4. Încarcă pe GitHub fișierul `radio/predici.json` modificat. Dacă folderul este o clonă git, folosește `--push` și scriptul îl încarcă singur.
5. Predica apare în radio după 1–2 minute. Archive.org poate avea nevoie de câteva minute să proceseze fișierul nou.

Pentru muzică, procedura e aceeași, cu `muzica` în loc de `predici` (MP3 stereo la 128 kbps). Opțiunea `--doar-local` face doar conversia, fără urcare, ca să verifici rezultatul.

## În Caietul de ucenicie
Varianta compactă a playerului: `https://<utilizator>.github.io/caiet/radio/?compact=1&canal=predici`. Integrarea în aplicație (bară de redare care rămâne activă cât navighezi) se face în pasul următor.

## De reținut
- **Live-ul de pe YouTube nu se poate prelua în radio.** Regulile YouTube interzic descărcarea, separarea sunetului de imagine și redarea în fundal.
  - Corect pentru live: în aplicație afișăm playerul YouTube, cu imaginea vizibilă.
  - Pentru un live doar audio: OBS trimite sunetul în paralel către un server Icecast propriu. Asta e o etapă ulterioară, pe un server gratuit Oracle Cloud cu AzuraCast.
- **Drepturi:**
  - **Predicile** sunt ale bisericii.
  - **Muzica** e mai delicată. Chiar interpretate de grupul de laudă, cântările au autori. Un radio online public cu muzică protejată are nevoie de licențe de la organismele de gestiune colectivă (UCMR-ADA pentru autori; CREDIDAM și UPFR pentru artiști și producători). Licența CCLI pentru streaming acoperă serviciile de închinare transmise online, nu un radio permanent.
  - Până la clarificare, pe canalul Muzică puneți doar înregistrări proprii ale unor cântări din domeniul public (imnuri vechi) sau cu acordul scris al autorilor.
