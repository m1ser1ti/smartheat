# SmartHeat hardware cost estimate (concept)

Prices in US dollars, checked on 18 November 2026. Prices change often, so treat them as a rough guide.
Hardware is not built yet; this is what a pilot would need.

## Per room

| Part | What it does | Price | Source |
|---|---|---|---|
| Seeed XIAO ESP32-C3 | Small Wi-Fi board that reads the sensors | $5.39 | [RobotShop](https://www.robotshop.com/products/seeedstudio-xiao-esp32c3-tiny-mcu-w-wi-fi-ble) |
| SHT40 sensor | Room temperature and humidity | $5.95 (1-9), $4.76 (100+) | [Adafruit 4885](https://www.adafruit.com/products/4885) |
| Magnetic window switch | Knows if the window is open | $3.95 (1-9), $3.16 (100+) | [Adafruit 375](https://www.adafruit.com/products/375) |
| LiPo battery 1200 mAh | Powers the sensor board | $9.95 | [Mouser 485-258](https://www.mouser.com/ProductDetail/485-258) |
| Box and wires | Housing | ~$2 | our estimate |
| Sonoff TRVZB smart radiator valve | Opens and closes the radiator | $27.90 | [Sonoff store](https://sonoff.tech/products/sonoff-zigbee-thermostatic-radiator-valve) |
| **Total per room** | | **~$55** (single units), **~$53** (100+) | |

## Per building (one gateway)

| Part | What it does | Price | Source |
|---|---|---|---|
| Raspberry Pi 5, 4 GB | Small computer that runs the model | $110 (2026 price after memory price rises) | [Liliputing](https://liliputing.com/?p=198888), [TweakTown](https://www.tweaktown.com/news/110841/raspberry-pi-hikes-prices-by-up-to-150-tries-cushion-the-blow-with-new-3gb-4-variant/index.html) |
| Sonoff ZBDongle-E | Talks to the radiator valves (Zigbee) | $29.95 | [Ameridroid](https://ameridroid.com/collections/all/products/sonoff-zigbee-3-0-usb-dongle-plus) |
| Raspberry Pi 27 W power supply | Power | ~$15 (£11.50) | [The Pi Hut](https://thepihut.com/collections/raspberry-pi-psus/products/raspberry-pi-27w-usb-c-power-supply) |
| microSD card and case | Storage and housing | ~$20 | our estimate |
| **Total per building** | | **~$175** | |

## Building with 100 rooms

| | Cost |
|---|---|
| 100 rooms x ~$53 | ~$5,316 |
| 1 gateway | ~$175 |
| **Total** | **~$5,500, about $55 per room** |

**Cheaper "lite" option:** only the smart valves and the gateway, no separate room sensors. The valve has its own
temperature sensor, but it measures next to the hot radiator and cannot see open windows. About **$30 per room**.

## Not included

- Installation work. Many older buildings have one-pipe heating systems, where a valve may need a bypass or a new valve
  body fitted by a plumber. This is the biggest unknown cost.
- Shipping, import duties and local taxes in Kazakhstan and Azerbaijan.
- Software: free and open source (Python, LightGBM, Open-Meteo for non-commercial use), runs on the gateway.

## Money and payback

Heat tariffs used (today's prices; installation not included):

- **Astana:** 4,061.11 KZT per Gcal excluding VAT, households with a building heat meter (Astana-Teplotranzit,
  October 2026 bills). Only metered buildings turn saved heat into a smaller bill, so we use the metered tariff.
- **Baku:** 14.60 AZN per Gcal including VAT, metered households (Tariff Council decision No. 17, 29.12.2024).
  No separate tariff for public buildings is published, so this is a lower bound.
- 1 Gcal = 1,163 kWh. Exchange rates on 24.11.2026: 455.12 KZT and 1.70 AZN per US dollar (national banks).

| City | Heat saved per room per season | Money per room per season | Payback, full kit (~$55) | Payback, lite (~$30) |
|---|---|---|---|---|
| Astana | 218-868 kWh (base 484) | 762-3,031 KZT (base 1,690 KZT, about $3.7) | 8-33 years (base 15) | 4.5-18 years (base 8) |
| Baku | 560-998 kWh (base 760) | 7.0-12.5 AZN (base 9.5 AZN, about $5.6) | 7.5-13 years (base 10) | 4-7 years (base 5) |

Payback (years) = cost per room / money saved per room per season. Numbers: `figures/savings_summary.json`.

**What this means:** at today's low, subsidised household tariffs the hardware pays back slowly. The strongest
benefits today are comfort (no overheating) and lower CO₂. Payback gets shorter with the lite kit, bulk prices,
buildings that pay higher tariffs, and the tariff growth expected in Kazakhstan.
