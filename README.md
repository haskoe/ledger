SELECT sum(position) WHERE account ~ 'SkyldigMoms' AND date >= "2026-01-01" AND date <= "2026-06-30" ORDER BY date ASC
SELECT sum(position) WHERE account ~ 'SkyldigMoms'GROUP BY 1

SELECT account, sum(position) WHERE account ~ "SkyldigMoms" AND date >= "2026-01-01" AND date <= "2026-06-30" GROUP BY 1