# Commercial Audio Asset Manifest

All audio files in this directory are published under the
[Creative Commons Zero 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/)
public-domain dedication. CC0 permits commercial use, modification, and
redistribution without attribution. Credits are retained below for provenance.

The two music files are unmodified byte copies of the named source files. The
Kenney sound effects were decoded from their original Ogg Vorbis files to
RIFF/WAVE PCM16 so they work with miniaudio's built-in decoders. Conversion
preserved each source's 44.1 kHz sample rate and mono/stereo channel layout;
no resampling, normalization, mixing, or other processing was applied.

Conversion used the public-domain
[stb_vorbis v1.22](https://github.com/nothings/stb/blob/master/stb_vorbis.c)
decoder. Converter source SHA256:
`4C7CB2FF1F7011E9D67950446B7EB9CA044F2E464D76BFBB0B84DD2E23E65636`.
Download/conversion date: **2026-08-10**.

## Music

### Funky Menu Loop

- Repository file: `Music/menu_funky_loop.wav`
- Original file: `funkymenuloop-longer.wav`
- Creator: iamoneabe
- Asset page: <https://opengameart.org/content/funky-menu-loop>
- Direct source: <https://opengameart.org/sites/default/files/funkymenuloop-longer.wav>
- License: CC0 1.0 (the asset page identifies the work as CC0/Public Domain)
- Format: stereo, 44.1 kHz, 16-bit WAV, 36.923 s
- SHA256: `FF0A933CC91FF8FCB71B000152993E659977D632FFA01DC791512B096E60E892`

### Fast Fight / Battle Music (Looped)

- Repository file: `Music/battle_fast_loop.wav`
- Original file: `fight_looped.wav`
- Loop edit creator: XCVG
- Original composer: Ville Nousiainen (Xythe / mutkanto)
- Asset page: <https://opengameart.org/content/fast-fight-battle-music-looped>
- Direct source: <https://opengameart.org/sites/default/files/fight_looped.wav>
- License: CC0 1.0 (the asset page identifies the work as CC0)
- Format: stereo, 44.1 kHz, 16-bit WAV, 24.765 s
- SHA256: `4E9614D4BC07E91E4D279199FBEF4AB1B02EC190E4C47F5D1741E44B25E87BA9`

## Kenney Interface Sounds 1.0

- Creator/distributor: Kenney (Kenney Vleugels), <https://kenney.nl/>
- Asset page: <https://kenney.nl/assets/interface-sounds>
- Official archive: <https://kenney.nl/media/pages/assets/interface-sounds/fa43c1dd4d-1677589452/kenney_interface-sounds.zip>
- License: CC0 1.0; the archive's `License.txt` explicitly permits commercial projects and makes credit optional.
- Archive SHA256: `F2193D072726D6758A5F7871B2DCC54DCCE0D5C35C6F0A62F92549B327C81232`

| Repository file | Original file / SHA256 | Derived format | Repository SHA256 |
| --- | --- | --- | --- |
| `SFX/UI/click.wav` | `Audio/click_001.ogg` / `CCFB7FA0CCCDD9FAEC0EB16033C732B1E308D139D80F799161495D58F7ADCDB9` | PCM16, 44.1 kHz, mono, 0.100 s | `E9E6703B095630AEE015D5B50AD95EC7F910D889029A2A0A20E6D67036FDFC72` |
| `SFX/UI/confirm.wav` | `Audio/confirmation_002.ogg` / `33B17A9A9A2397C62B285C52C33A907FDFFB476909C99E42DDE603F6A7A8B12C` | PCM16, 44.1 kHz, mono, 0.539 s | `50C019BF6A203C2B6FCF74319A12609009EE227526C52B5B4954D47CC8E49BBD` |
| `SFX/UI/error.wav` | `Audio/error_003.ogg` / `885B28175C7B511118BCFFAB95675B48BBAC9005CF6514656EBDAD979276B3AB` | PCM16, 44.1 kHz, stereo, 0.533 s | `B0642A2AA34762F18F19399B88EC39DC567CA7BE2DBC9F5207AC8608740025B1` |

## Kenney Digital Audio

- Creator/distributor: Kenney Vleugels, <https://kenney.nl/>
- Asset page: <https://kenney.nl/assets/digital-audio>
- Official archive: <https://kenney.nl/media/pages/assets/digital-audio/216eac4753-1677590265/kenney_digital-audio.zip>
- License: CC0 1.0; the archive's `License.txt` explicitly permits commercial projects and makes credit optional.
- Archive SHA256: `24E6CE28B76A6D8C89CFF4D331E0965FF5C3DE8A73C612028E9D363CC64E4F06`

| Repository file | Original file / SHA256 | Derived format | Repository SHA256 |
| --- | --- | --- | --- |
| `SFX/Gameplay/level_up.wav` | `Audio/powerUp1.ogg` / `8C361B624B560C0BC30EA3063B71212BC30CAEBF425C9DF2481C13B25561485C` | PCM16, 44.1 kHz, mono, 1.202 s | `B6AB4BBABAAD99BAEF8E4D5EFF99DF70A23FD24EF3F21BCAEAE289332D0FC9F7` |
| `SFX/Gameplay/xp_pickup.wav` | `Audio/pepSound3.ogg` / `5E9F2B4A0B14E65A157D0BBCB28CF816926583AFA96E753489C722EC3D810A78` | PCM16, 44.1 kHz, mono, 0.444 s | `D9196A1F717E092450BE0886B71D12DE9B9F04C04CF04768DCCC06B63979A07D` |
| `SFX/Gameplay/boss_alert.wav` | `Audio/lowThreeTone.ogg` / `B4B3BC7420E71BFBEC49A6EA13B8C12D76A5751CBDF063D8A8AC017C0B1E1D87` | PCM16, 44.1 kHz, mono, 1.019 s | `061C038FBE03CE130D51A2BDF965A128A5FEDA4A50C41C36807F2D33FDC45893` |
| `SFX/Gameplay/cast_light.wav` | `Audio/phaseJump2.ogg` / `5D85717CFCA231F7DA7887CEF5F44B2131BBE3308EB0C1FEE0B4F9E61D59B571` | PCM16, 44.1 kHz, stereo, 0.392 s | `15874BE00366EAD2EF5EF87F70F34396BB01A846449F8598ACA7A6BFC062E56D` |
| `SFX/Gameplay/cast_energy.wav` | `Audio/phaserUp6.ogg` / `39616FBEB3CF28288873502E99ACFC590705D54BF7F58EF3F1A23CEC72DD22DB` | PCM16, 44.1 kHz, stereo, 0.340 s | `F66EFAAC80140B4142D6258DB2630956A3FD0E59237F56EF39B16516267D89BE` |
| `SFX/Gameplay/cast_heavy.wav` | `Audio/zap1.ogg` / `4E4BF11C671A4BE0723022A7177F8E122329FA32A0C59555581F4193ED111585` | PCM16, 44.1 kHz, mono, 1.019 s | `C841AB022AB224685AB0FDF9F1B4457247860AC9520B0ABA6C8026EC8F371182` |

## Kenney Impact Sounds 1.0

- Creator/distributor: Kenney, <https://kenney.nl/>
- Asset page: <https://kenney.nl/assets/impact-sounds>
- Official archive: <https://kenney.nl/media/pages/assets/impact-sounds/87b4ddecda-1677589768/kenney_impact-sounds.zip>
- License: CC0 1.0; the archive's `License.txt` explicitly permits commercial projects and makes credit optional.
- Archive SHA256: `029D734AF1582474EDF3A694D1B0CEBC97C1C152F2F39FA34D4C2BAFC5DE77F8`

| Repository file | Original file / SHA256 | Derived format | Repository SHA256 |
| --- | --- | --- | --- |
| `SFX/Gameplay/monster_hit_01.wav` | `Audio/impactSoft_medium_000.ogg` / `7D3BA0BB5E60A11B5D3E558C141303DCF494256675FBF753C0D252D2CF0481E3` | PCM16, 44.1 kHz, stereo, 0.118 s | `4189F9260905DE4CC29AD364BB88BC3BBE02DE52B8AAC42C5C312B9412CCEA24` |
| `SFX/Gameplay/monster_hit_02.wav` | `Audio/impactSoft_medium_001.ogg` / `7642A4FD43E547AFE4F7ADFADB3DABB681C0FF512F52C1674BAE30A726841FAF` | PCM16, 44.1 kHz, stereo, 0.183 s | `B2810488CF8F5CE15976FCC14C957D4B148233A952E4B0327B31559DC433E78A` |
| `SFX/Gameplay/monster_hit_03.wav` | `Audio/impactSoft_medium_002.ogg` / `5069E3571A77D7F7AAE9EF71D0364AA245FB7D64A7C8CC9956F221D03088C089` | PCM16, 44.1 kHz, stereo, 0.135 s | `72DF7115B3FB248A94A285DCDDE76027C2F075B7D1DA1FCA89B85965AB98A1B0` |
| `SFX/Gameplay/monster_death_01.wav` | `Audio/impactSoft_heavy_000.ogg` / `49E7CA88743FCA974BB8676EA138B751CFD8F9033B5E7AF8736C2A215D6EDBC1` | PCM16, 44.1 kHz, stereo, 0.505 s | `E374DAAE52C57106FDADB8EE0C1EA64B5BE9518B31717E632483C1A2E2B90CC7` |
| `SFX/Gameplay/monster_death_02.wav` | `Audio/impactSoft_heavy_001.ogg` / `4D0096364BA9E46119D2FF6DF493FDC101BD2E1EFAE061DA5E5F77A53B3FDCB6` | PCM16, 44.1 kHz, stereo, 0.572 s | `6943B4C4BF875D6F62D35779E7300C08FAE10371CC35F7368D1C73958AE27D46` |
| `SFX/Gameplay/player_hit.wav` | `Audio/impactPunch_medium_002.ogg` / `6492F9CCBC8D24DCEF607BB1B48790B7870961474561F7FE5601E1C73A3018EF` | PCM16, 44.1 kHz, stereo, 0.541 s | `FB1532B7F237308D169F11CE0FED7B0FE3142D5EA878005511C60D87F0F75DEC` |

## Selection intent

- The menu and battle tracks are loop-oriented and are intended to stream from the Music bus.
- UI sounds are short and distinct so menu navigation remains readable while gameplay is paused.
- Three soft hit variants and two soft death variants avoid repetitive, realistic gore sounds when many monsters are active.
- Digital rise, phase, and zap sounds fit the game's cute magical weapons; the event bank limits their overlap.
