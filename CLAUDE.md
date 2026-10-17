# CLAUDE.md — Warsaw Open Data Hackathon, Wyzwanie 2: „Warszawa – złap oddech!”

Ten plik czyta każda sesja Claude w zespole. Trzymaj go krótkim i aktualnym.

## Wyzwanie
Pomóż warszawiakom: znaleźć równowagę praca–życie,  odkrywać Warszawę na nowo,
być na bieżąco z tym, co dzieje się w mieście. 

## Twarde wymagania
- Rozwiązanie MUSI korzystać z danych z https://dane.um.warszawa.pl/ — i musi to być widać na demo.
- Koniec kodowania: niedziela 11:00, punktualnie. Potem tylko prezentacja.
- Pracujemy na własnych laptopach.

## Kryteria jury (optymalizuj pod nie każdą decyzję)
| Kryterium | Waga | Co to znaczy dla nas |
|---|---|---|
| Wykorzystanie otwartych danych m.st. Warszawy | 20% | ≥2–3 zbiory, połączone ze sobą, źródło pokazane w UI |
| Innowacyjność i pomysłowość | 25% | Jedna wyraźna „nowa” rzecz, nie kolejna mapa z pinezkami |
| Praktyczne zastosowanie, potencjał wdrożeniowy | 20% | Konkretny użytkownik, konkretna sytuacja, da się utrzymać |
| Związek z wyzwaniami i realiami Warszawy | 15% | Dzielnice, ZTM, Veturilo, parki, lokalne wydarzenia |
| Jakość prezentacji | 20% | Działające demo + historia jednej osoby + liczby |

## Pomysł (wypełnia lider po fazie ideacji, max 13:00 w sobotę)
Jeszcze nie mamy konkretnego pomysłu i musimy zrobić eksplorację 

## Stack (zmień przed startem, potem nie zmieniaj)
- Dane/ETL: Python 3.11, `httpx`, `pandas`/`geopandas`; skrypty w `scripts/`, 
- Backend: FastAPI (`backend/`), serwuje endpointy z JSON/GeoJSON z gotowymi danymi
- Frontend: React.js + Tailwind + MapLibre/Leaflet (`frontend/`)
- Deploy: nie wiadomo
- Sekrety: `.env` (nigdy do gita), wzór w `.env.example`

## Zasady pracy dla Claude
- Nie zmieniaj stacku ani struktury katalogów bez decyzji zapisanej w „Dziennik decyzji”.
- Pracuj tylko w swoim obszarze (patrz „Podział”). Kontrakty między obszarami są w `docs/API.md` — zmiana kontraktu = najpierw edycja `docs/API.md`, potem kod.
- Nigdy nie odpytuj API miasta w czasie żądania użytkownika, jeśli da się użyć cache z `data/`. API może paść albo limitować w trakcie demo.
- Nie generuj fikcyjnych danych udających miejskie. Mock tylko z etykietą `MOCK` i tylko tymczasowo.
- Odpowiadaj zwięźle, po polsku w komunikacji, kod i nazwy w kodzie po angielsku.

