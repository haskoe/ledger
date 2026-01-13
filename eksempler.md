# Posteringer

## salg
faktura udstedt
2021-01-31 * "salg" "Salg GOTTIT. Periode jan. Timer: 33.0 * 900.0 = 29700.0"
  Income:Salg:GOTTIT                                           -29,700.00 DKK
  Liabilities:Moms:SalgMoms                                     -7,425.00 DKK
  Assets:Debitorer                                              37,125.00 DKK

faktura betalt
2021-12-02 * "salg_betalt betalt" "f.nr. 202109 betalt"
  Assets:Debitorer:GOTTIT                                      -72,000.00 DKK
  Assets:Bank:BankErhverv                                       72,000.00 DKK

## køb med moms
2021-12-10 * "udgift_med_moms" "Elgiganten.dk, Koebenhavn S Notanr 31872"
  Expenses:Hardware:ELG                                           1039.20 DKK
  Assets:Moms:KoebMoms                                             259.80 DKK
  Liabilities:Kreditorer                                         -1299.00 DKK

## køb med moms betalt
2021-12-10 * "udgift_med_moms_betalt" "Elgiganten.dk, Koebenhavn S Notanr 31872"
  Liabilities:Kreditorer                                          1299.00 DKK
  Assets:Bank:BankErhverv                                        -1299.00 DKK

## acontoskat
Betaling af acontoskat (løbende)
2025-03-20 * "SKAT" "Betaling af 1. rate acontoskat"
  Assets:Bank                 -10000.00 DKK
  Assets:Acontoskat            10000.00 DKK

Ved regnskabsafslutning (hensættelse)  
2025-12-31 * "Regnskabsafslutning" "Beregnet selskabsskat for 2025"
  Expenses:Skat                25000.00 DKK
  Assets:Acontoskat           -20000.00 DKK
  Liabilities:Skattefond       -5000.00 DKK

Betaling af restskat (næste år)
2026-11-20 * "SKAT" "Betaling af restskat for 2025"
  Liabilities:Skattefond        5000.00 DKK
  Assets:Bank                  -5000.00 DKK

# BQL
SELECT sum(position) WHERE account ~ 'SkyldigMoms' AND date >= "2026-01-01" AND date <= "2026-06-30" ORDER BY date ASC
SELECT sum(position) WHERE account ~ 'SkyldigMoms'GROUP BY 1
SELECT account, sum(position) WHERE account ~ "SkyldigMoms" AND date >= "2026-01-01" AND date <= "2026-06-30" GROUP BY 1

# dannelse af transaktioner

## posteringer udledt fra banktransaktioner
transaktion kan dannes direkte med 1) udledt konto med beløb med modsat fortegn og 2) bankkonto med beløb (som regel minus)

## salg
moms (som regel) med 3 konti:
1) Income:Salg, -(momsbelagt + momsfrit)
2) Liabilities:Moms:SalgMoms, -momsbeløb
3) Assets:Debitorer, -(beløb1 + beløb2)

## Løn
4 stk. 2-konto transaktioner (ATP,Gebyr,Skat,Ansat)
1) Expenses:Loen:<konto> + 
2) Expenses:Loen:<konto> -
