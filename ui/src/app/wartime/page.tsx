'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2, AlertTriangle } from 'lucide-react';
import AppShell from '@/components/AppShell';
import { apiFetchJson } from '@/lib/api';
import { applyChartTheme } from '@/lib/chartTheme';
import { useTheme } from '@/context/ThemeContext';

// ─── Types ────────────────────────────────────────────────────────────────────

type Lang = 'en' | 'ko';

interface RebasedSeries { x: number[]; y: number[] }

interface SpxStat {
  conflict: string; start_date: string; mdd: number; days_to_bottom: number;
  recovery_days: number | null; final_return: number; days_avail: number; note: string | null;
}

interface CommodityStat {
  conflict: string; start_date: string; peak_gain: number; days_to_peak: number;
  mdd: number; final_return: number; days_avail: number; note: string | null;
}

interface WartimeFigure {
  data: any[];
  layout: any;
}

interface WartimeData {
  conflicts: Record<string, { start_date: string; note: string | null }>;
  spx:  { rebased: Record<string, RebasedSeries>; stats: SpxStat[] };
  gold: { rebased: Record<string, RebasedSeries>; stats: CommodityStat[] };
  oil:  { rebased: Record<string, RebasedSeries>; stats: CommodityStat[] };
  current: {
    name: string; spx_days_elapsed: number;
    spx_return: number | null; spx_low: number | null;
    gold_return: number | null; oil_return: number | null;
  };
  summary: {
    avg_mdd: number | null; avg_bottom_days: number | null;
    avg_recovery_days: number | null; recovery_rate: number | null;
  };
}

// ─── Translations ─────────────────────────────────────────────────────────────

const CONFLICT_NAMES_KO: Record<string, string> = {
  'Gulf War (1990)':                    '걸프전 (1990)',
  'Kosovo/NATO Airstrikes (1999)':      '코소보/NATO 공습 (1999)',
  '9/11 / Afghanistan (2001)':          '9/11 테러 / 아프가니스탄 (2001)',
  'Iraq War Invasion (2003)':           '이라크 전쟁 침공 (2003)',
  'Libya/Arab Spring (2011)':           '리비아/아랍의 봄 (2011)',
  'ISIS/Iraq Crisis (2014)':            'ISIS/이라크 위기 (2014)',
  'US-Syria Airstrikes (2017)':         '미국-시리아 공습 (2017)',
  'Soleimani/Iran Strike (2020)*':      '솔레이마니/이란 공습 (2020)*',
  'Russia-Ukraine Invasion (2022)':     '러시아-우크라이나 침공 (2022)',
  'Israel-Hamas War (2023)':            '이스라엘-하마스 전쟁 (2023)',
  'Iran Attack — Current (2026-02-28)': '이란 공격 — 현재 (2026-02-28)',
};

const T = {
  en: {
    title: 'Wartime Market Analysis',
    subtitle: 'S&P 500 / Gold / WTI performance over 200 trading days following major geopolitical conflicts.',
    analysisDate: 'Analysis date: 2026-02-28',
    langToggle: '한국어',
    loading: 'Loading analysis…',
    loadError: 'Failed to load wartime data. The backend may be unavailable.',

    commentaryLabel: 'Market Commentary',
    commentaryText: [
      'We anticipate near-term risk-off assets like gold, US Treasuries, and defensive sectors to outperform equities until geopolitical visibility improves. ',
      'Amidst EM equities, ', 'India', ' remains highly vulnerable; every USD 10/bbl spike in oil worsens its CAD by 0.4–0.5% and structurally raises ',
      'inflation by 0.3–0.5%. ', 'China', ' has built substantial strategic petroleum reserves, providing a short-term buffer, while ', 'Brazil', ' is a net oil exporter and actually benefits from higher energy ',
      'prices. Asian tech exporters such as ', 'Taiwan', ' and ', 'Korea', ' face dual headwinds: they are heavy oil importers and ',
      'highly sensitive to global consumer demand shocks. However, historically, when WTI approaches USD 75–80/bbl, US shale producers rapidly ramp up ',
      'drilling activity within months, creating a natural ceiling for oil prices. We suggest maintaining strategic asset allocations while hedging tail risks. As the ',
      'conflict remains fluid, any credible de-escalation news will likely trigger aggressive short-covering and flows back into risk assets, mirroring past geopolitical turmoil recoveries.',
    ],

    spxTitle: 'S&P 500',
    spxSubtitle: '— Cumulative Performance',
    spxChartTitle: 'S&P 500 — Cumulative Performance Since Conflict Onset',
    spxYAxis: 'Rebased (1.0 = day 0)',
    spxXAxis: 'Trading days since conflict onset',
    spxTableLabel: 'Conflict-by-conflict statistics',
    spxCovid: '* 2020 Soleimani strike overlapped with COVID-19 — treat as outlier.',
    spxSummaryTitle: 'S&P 500 Historical Averages (excl. current)',

    thConflict: 'Conflict',
    thStart: 'Start',
    thMdd: 'MDD',
    thDaysToLow: 'Days to Low',
    thRecovery: 'Recovery',
    thFinalRet: 'Final Ret.',
    thPeakGain: 'Peak Gain',
    thDaysToPeak: 'Days to Peak',
    thMddFromPeak: 'MDD from Peak',
    notRecovered: '—',

    barMddTitle: 'Max Drawdown',
    barBottomTitle: 'Days to Low',
    barRecoveryTitle: 'Recovery Days',
    barMddHover: 'MDD (%)',
    barBottomHover: 'Days',
    barRecoveryHover: 'Days',

    avgMdd: 'Avg Max Drawdown',       avgMddSub: 'Historical conflicts',
    avgBottom: 'Avg Days to Low',     avgBottomSub: 'Trading days',
    avgRecovery: 'Avg Recovery',      avgRecoverySub: 'Days from low to breakeven',
    recoveryRate: 'Recovery Rate',    recoveryRateSub: 'Recovered within 200 days',

    goldTitle: 'Gold',
    goldSubtitle: '— Safe Haven Performance',
    goldChartTitle: 'Gold — Cumulative Performance Since Conflict Onset',
    goldYAxis: 'Rebased Gold Price (1.0 = day 0)',
    goldTableLabel: 'Commodity stats — Gold',
    goldNote: 'Gold typically benefits from safe-haven demand during geopolitical conflicts. "MDD from Peak" shows how much of the initial spike was subsequently given back.',

    oilTitle: 'WTI Crude',
    oilSubtitle: '— Supply Risk Premium',
    oilChartTitle: 'WTI Crude — Cumulative Performance Since Conflict Onset',
    oilYAxis: 'Rebased WTI Price (1.0 = day 0)',
    oilTableLabel: 'Commodity stats — WTI',
    shaleTitle: 'Shale supply buffer:',
    shaleText: 'When WTI reaches USD 60–70/bbl, US shale producers can ramp up drilling within months — meaning oil price spikes from geopolitical events tend to be self-limiting in the medium term.',

    emTitle: 'EM Oil Price Shock Exposure',
    emSubtitle: 'Estimated impact of a USD 10/bbl crude price increase',
    emThCountry: 'Country', emThStance: 'Stance', emThAssessment: 'Assessment',
    emRows: [
      { country: 'India',  flag: '🔴', stance: 'Vulnerable',  stanceKo: '취약', desc: 'Net oil importer — $10/bbl spike worsens CAD by 0.4–0.5% and raises inflation 0.3–0.5%' },
      { country: 'Taiwan', flag: '🔴', stance: 'Vulnerable',  stanceKo: '취약', desc: 'Net oil importer — energy cost surge squeezes manufacturing margins' },
      { country: 'Korea',  flag: '🔴', stance: 'Vulnerable',  stanceKo: '취약', desc: 'Net oil importer — trade balance deteriorates, KRW depreciation pressure' },
      { country: 'China',  flag: '🟡', stance: 'Buffered',    stanceKo: '완충', desc: 'Strategic reserves buffer short-term shock; medium-term uncertainty remains' },
      { country: 'Brazil', flag: '🟢', stance: 'Beneficiary', stanceKo: '수혜', desc: 'Net oil exporter — higher energy prices boost trade balance and fiscal revenue' },
    ],

    iranTitle: 'Iran Attack — Live Snapshot',
    cardDaysElapsed: 'Days Elapsed',      cardDaysElapsedSub: 'Trading days since onset',
    cardSpxReturn: 'S&P 500 Return',      cardSpxReturnSub: 'Cumulative since 2026-02-28',
    cardSpxLow: 'S&P 500 Low',           cardSpxLowSub: 'Intra-period trough',
    cardGoldReturn: 'Gold Return',        cardGoldReturnSub: 'Cumulative since 2026-02-28',
    cardOilReturn: 'WTI Return',          cardOilReturnSub: 'Cumulative since 2026-02-28',

    scenariosTitle: 'Historical Precedent Scenarios',
    bullLabel: 'Bull scenario — rapid recovery',
    bullAnalogues: 'Analogues: Iraq War (2003), Kosovo (1999), Gulf War (1990)',
    bullDrawdown: '-3% to -7%',
    bullRecovery: '30–60 trading days',
    bull200d: '+5% to +15%',
    bullText: 'If the Iran strike is isolated and escalation is contained, history suggests an initial shock followed by a rapid recovery as liquidity returns to risk assets.',
    bearLabel: 'Bear scenario — prolonged shock',
    bearAnalogues: 'Analogues: 9/11 (2001), Soleimani (2020)*',
    bearDrawdown: '-10% to -25%+',
    bearRecovery: '100–200+ trading days',
    bear200d: '-5% to +5%',
    bearText: 'Full regional war expansion or oil supply disruption reigniting inflation would create sustained downward pressure. Medium-term damage depends on Fed response.',
    rowExpectedDrawdown: 'Expected drawdown',
    rowRecoveryTimeline: 'Recovery timeline',
    row200dReturn: '200-day return',

    covidTitle: '2020 Soleimani Strike — COVID-19 Distortion Warning',
    covidText1: 'The January 3, 2020 Soleimani airstrike coincided perfectly with the onset of the COVID-19 pandemic. The S&P 500 ultimately suffered a -34% drawdown, but this was entirely driven by the pandemic lockdown — an independent black-swan event — and not the geopolitical shock. Direct comparison with the 2026 Iran attack fundamentally distorts base rate expectations.',
    covidText2: 'Key takeaway: The broader macroeconomic environment (inflation trajectory, Fed policy stance, consumer balance sheets) overwhelmingly dictates the market\'s recovery speed, not just the isolated magnitude of the geopolitical event itself.',
    covidCaution: 'requires caution',

    monitoringTitle: 'Key Monitoring Indicators',
    monThMetric: 'Indicator', monThBull: 'Bull Signal', monThBear: 'Bear Signal',
    monRows: [
      { metric: 'WTI/Brent Oil',      bull: 'Stays below $85',              bear: 'Breaks and holds above $95' },
      { metric: 'VIX',                bull: 'Crushes back below 18 quickly', bear: 'Spikes and stays above 30' },
      { metric: 'DXY (Dollar Index)', bull: 'Stable or weakens',            bear: 'Sharp rally (risk-off flight)' },
      { metric: 'Iran Escalation',    bull: 'Isolated strike, no follow-up', bear: 'Strait of Hormuz closure threat' },
      { metric: 'Fed Response',       bull: 'Preemptive liquidity/easing',   bear: 'Hawkish pause on inflation fears' },
      { metric: 'Israel/Mid-East',    bull: 'Contained measured response',   bear: 'Full multi-front regional war' },
    ],
    disclaimer: 'This analysis is based on historical precedents and is for informational purposes only — not investment advice. Situation as of 2026-02-28 and subject to rapid change.',
  },

  ko: {
    title: '전시 증시 분석',
    subtitle: 'S&P 500 / 금 / WTI 원유: 주요 지정학적 갈등 발생 후 200거래일 성과 분석',
    analysisDate: '분석 기준일: 2026-02-28',
    langToggle: 'English',
    loading: '데이터 로딩 중…',
    loadError: '데이터를 불러올 수 없습니다. 백엔드 서버를 확인하세요.',

    commentaryLabel: '시장 분석 요약',
    commentaryText: [
      '단기적으로 방어주, 금, 미 국채 등 리스크오프(안전자산 선호) 자산이 주식 등 위험자산 대비 강력한 아웃퍼폼을 보일 것으로 전망합니다. ',
      '신흥국(EM) 증시 내에서 ', '인도', '는 특히 취약성이 두드러집니다. 유가가 배럴당 10달러 상승할 때마다 경상수지 적자가 0.4~0.5%p 확대되고 헤드라인 인플레이션이 ',
      '0.3~0.5%p 구조적으로 상승합니다. ', '중국', '은 대규모 전략비축유(SPR)를 확보하여 단기 충격 완충력이 있으며, 원유 순수출국인 ', '브라질', '은 오히려 ',
      '에너지 가격 상승의 수혜를 직접적으로 누리게 됩니다. 반면 펀더멘털 상 ', '대만', '과 ', '한국', ' 등 아시아 기술주 중심 수출국들은 원유를 전량 수입에 의존할 뿐만 아니라, ',
      '글로벌 소비 둔화 리스크까지 겹치는 이중고(dual headwinds)에 노출되어 있습니다. 다만, 과거 사례를 볼 때 WTI가 75~80달러선에 근접하면 미국 셰일(Shale) 오일 생산자들이 수개월 내 가동률을 급격히 끌어올리며 유가의 자연적 상단(natural ceiling)을 형성해 왔습니다. ',
      '현재 불확실성이 극도로 높은 국면이므로 꼬리 위험(tail risk)을 헤지하되, 장기 자산배분 전략을 훼손하지 않을 것을 권고합니다. ',
      '사태 양상이 매우 유동적이므로, 신뢰도 높은 확전 자제 및 긴장 완화(de-escalation) 뉴스가 보도될 경우 즉각적인 숏커버링과 함께 리스크 자산으로의 대규모 자금 팽창이 재개될 가능성이 큽니다.',
    ],

    spxTitle: 'S&P 500',
    spxSubtitle: '— 갈등 발생 후 누적 성과',
    spxChartTitle: 'S&P 500 — 갈등 발생 후 누적 성과 (리베이스 = 1.0)',
    spxYAxis: '리베이스 성과 (1.0 = 시작)',
    spxXAxis: '거래일 (갈등 발생 기준)',
    spxTableLabel: '갈등별 시장 반응 통계',
    spxCovid: '* 2020년 솔레이마니 공습은 COVID-19 팬데믹과 겹쳐 단순 비교에 주의 요망.',
    spxSummaryTitle: 'S&P 500 역사적 평균 (현재 이란 제외)',

    thConflict: '갈등',
    thStart: '시작일',
    thMdd: '최대 낙폭',
    thDaysToLow: '저점 도달(거래일)',
    thRecovery: '회복 소요일',
    thFinalRet: '최종 수익률',
    thPeakGain: '최대 상승',
    thDaysToPeak: '정점 도달(거래일)',
    thMddFromPeak: '최대 낙폭(정점比)',
    notRecovered: '미회복',

    barMddTitle: '최대 낙폭 분포',
    barBottomTitle: '저점 도달 거래일',
    barRecoveryTitle: '회복 소요일',
    barMddHover: '낙폭(%)',
    barBottomHover: '거래일',
    barRecoveryHover: '거래일',

    avgMdd: '평균 최대 낙폭',      avgMddSub: '역사적 갈등 평균',
    avgBottom: '평균 저점 도달',   avgBottomSub: '거래일 기준',
    avgRecovery: '평균 회복 소요', avgRecoverySub: '저점에서 손익분기까지',
    recoveryRate: '200일 내 회복률', recoveryRateSub: '200거래일 내 회복 비율',

    goldTitle: '금 (Gold)',
    goldSubtitle: '— 안전자산 성과',
    goldChartTitle: '금(Gold) — 갈등 발생 후 누적 성과',
    goldYAxis: '리베이스 금 가격 (1.0 = 시작)',
    goldTableLabel: '상품 통계 — 금',
    goldNote: '금은 지정학적 갈등 시 안전자산 수요 증가로 단기 상승하는 경향이 있습니다. "최대 낙폭(정점比)"는 상승분이 얼마나 반납됐는지를 나타냅니다.',

    oilTitle: 'WTI 원유',
    oilSubtitle: '— 공급 리스크 프리미엄',
    oilChartTitle: 'WTI 원유 — 갈등 발생 후 누적 성과',
    oilYAxis: '리베이스 WTI 가격 (1.0 = 시작)',
    oilTableLabel: '상품 통계 — WTI',
    shaleTitle: '셰일 공급 완충 효과:',
    shaleText: 'WTI가 60~70달러/배럴 수준에 도달하면 미국 셰일 생산자들이 수개월 내 생산을 늘릴 수 있어, 지정학적 이벤트로 인한 유가 급등은 중기적으로 자기제한적(self-limiting)인 경향이 있습니다.',

    emTitle: '원유 가격 충격의 EM 국가별 영향',
    emSubtitle: 'USD 10/배럴 상승 기준 추정 영향',
    emThCountry: '국가', emThStance: '구분', emThAssessment: '평가',
    emRows: [
      { country: '인도',  flag: '🔴', stance: 'Vulnerable',  stanceKo: '취약',  desc: '원유 순수입국 — $10/bbl 상승 시 CAD +0.4~0.5%p, 인플레이션 +0.3~0.5%p' },
      { country: '대만',  flag: '🔴', stance: 'Vulnerable',  stanceKo: '취약',  desc: '원유 순수입국 — 에너지 비용 급등, 제조업 마진 압박' },
      { country: '한국',  flag: '🔴', stance: 'Vulnerable',  stanceKo: '취약',  desc: '원유 순수입국 — 무역수지 악화, 원화 약세 압력' },
      { country: '중국',  flag: '🟡', stance: 'Buffered',    stanceKo: '완충',  desc: '전략비축유 보유 — 단기 충격 완화 가능, 중기 불확실성 존재' },
      { country: '브라질', flag: '🟢', stance: 'Beneficiary', stanceKo: '수혜', desc: '원유 순수출국 — 에너지 가격 상승이 무역수지·재정에 긍정적' },
    ],

    iranTitle: '이란 공격 (2026-02-28) — 현황',
    cardDaysElapsed: '경과 거래일',    cardDaysElapsedSub: '갈등 발생 이후',
    cardSpxReturn: 'S&P 500 수익률',   cardSpxReturnSub: '2026-02-28 기준 누적',
    cardSpxLow: 'S&P 500 저점',        cardSpxLowSub: '기간 중 최저점',
    cardGoldReturn: '금 수익률',        cardGoldReturnSub: '2026-02-28 기준 누적',
    cardOilReturn: 'WTI 수익률',        cardOilReturnSub: '2026-02-28 기준 누적',

    scenariosTitle: '역사적 선례 기반 시나리오',
    bullLabel: '낙관 시나리오 — 빠른 회복',
    bullAnalogues: '유사 선례: 이라크 전쟁(2003), 코소보(1999), 걸프전(1990)',
    bullDrawdown: '-3% ~ -7%',
    bullRecovery: '30~60 거래일',
    bull200d: '+5% ~ +15%',
    bullText: '이란 공격이 단발성 군사 행동에 그치고 확전이 제한될 경우, 과거 사례처럼 초기 충격 후 빠른 반등이 나타날 가능성이 높습니다.',
    bearLabel: '비관 시나리오 — 장기 충격',
    bearAnalogues: '유사 선례: 9/11(2001), 솔레이마니(2020)*',
    bearDrawdown: '-10% ~ -25%+',
    bearRecovery: '100~200 거래일 이상',
    bear200d: '-5% ~ +5%',
    bearText: '이란 공격이 중동 전면전으로 확대되거나, 원유 공급 차질로 인플레이션이 재점화될 경우 중장기 하방 압력이 증가합니다.',
    rowExpectedDrawdown: '예상 낙폭',
    rowRecoveryTimeline: '회복 예상',
    row200dReturn: '200일 후 예상',

    covidTitle: '2020년 솔레이마니 공습 — COVID-19 왜곡 경고',
    covidText1: '2020년 1월 3일 미국 솔레이마니 사령관 공습 직후 S&P 500은 최종 -34% 폭락했으나, 이는 전적으로 COVID-19 팬데믹이라는 독립적인 블랙스완 사태에 기인합니다. 팬데믹과 일정이 우연히 겹치며 낙폭이 극대화된 사례이므로, 2026년 이란-이스라엘 사태에 기초통계로 직접 대입할 경우 심각한 왜곡이 발생합니다. 직접 비교에는 ',
    covidText2: '핵심 교훈: 지정학적 이벤트 자체의 충격량보다는 시점의 거시 경제 환경(연준의 금리인하 여력, 물가 궤적, 소비자 심리)이 최종 저점과 회복 속도를 결정하는 최우선 변수입니다.',
    covidCaution: '주의가 필요합니다',

    monitoringTitle: '핵심 모니터링 지표',
    monThMetric: '지표', monThBull: '낙관 신호', monThBear: '비관 신호',
    monRows: [
      { metric: '원유 (WTI/Brent)',      bull: '$90 이하 유지',         bear: '$100 돌파 및 유지' },
      { metric: 'VIX (변동성 지수)',     bull: '20 이하 빠른 하락',     bear: '30 이상 지속' },
      { metric: '달러 인덱스 (DXY)',     bull: '안정 또는 약달러',      bear: '급등 (위험회피 심화)' },
      { metric: '이란 확전 여부',        bull: '단발성 공격 종결',      bear: '호르무즈 해협 봉쇄 위협' },
      { metric: '미국 연준 반응',        bull: '통화 완화 신호',        bear: '인플레 우려로 금리 동결' },
      { metric: '이스라엘/중동 연계',   bull: '충돌 범위 제한',        bear: '중동 전면전 확대' },
    ],
    disclaimer: '본 분석은 역사적 선례에 기반한 참고 자료이며, 투자 조언이 아닙니다. 2026년 2월 28일 기준 진행 중인 사건으로 상황은 빠르게 변화할 수 있습니다.',
  },
} as const;

// ─── Formatting helpers ───────────────────────────────────────────────────────

function pct(v: number | null, decimals = 1): string {
  if (v === null || v === undefined) return 'N/A';
  return `${v >= 0 ? '+' : ''}${(v * 100).toFixed(decimals)}%`;
}

function absLow(v: number | null): string {
  if (v === null || v === undefined) return 'N/A';
  return `${(v * 100).toFixed(1)}%`;
}

function clonePlotValue<T>(value: T): T {
  if (typeof structuredClone === 'function') {
    return structuredClone(value);
  }
  return JSON.parse(JSON.stringify(value));
}

function stripUndefinedDeep<T>(value: T): T {
  if (Array.isArray(value)) {
    return value
      .filter((item) => item !== undefined)
      .map((item) => stripUndefinedDeep(item)) as T;
  }

  if (value && typeof value === 'object') {
    const cleanedEntries = Object.entries(value as Record<string, unknown>)
      .filter(([, entryValue]) => entryValue !== undefined)
      .map(([key, entryValue]) => [key, stripUndefinedDeep(entryValue)]);
    return Object.fromEntries(cleanedEntries) as T;
  }

  return value;
}

// ─── Chart builders ───────────────────────────────────────────────────────────

const COLOR_CURRENT = '#FF4B4B';
const COLOR_COVID   = '#FFA500';
const COLOR_GOLD    = '#FFD700';
const COLOR_OIL     = '#F97316';

function buildLineChart(
  rebased: Record<string, RebasedSeries>,
  title: string,
  yTitle: string,
  xTitle: string,
  theme: string,
  lang: Lang,
) {
  const nameOf = (n: string) => lang === 'ko' ? (CONFLICT_NAMES_KO[n] ?? n) : n;
  const refLineColor = theme === 'dark' ? 'rgba(148,163,184,0.4)' : 'rgba(100,116,139,0.35)';

  const data: any[] = Object.entries(rebased).map(([name, series]) => {
    const isCurrent = name.includes('Current');
    const isCovid   = name.includes('2020');
    const label     = nameOf(name);
    return stripUndefinedDeep({
      x: series.x, y: series.y, name: label,
      type: 'scatter',
      mode: isCurrent ? 'lines+markers' : 'lines',
      line: isCurrent
        ? { width: 3, color: COLOR_CURRENT, dash: 'dot' }
        : isCovid ? { width: 2.5, color: COLOR_COVID, dash: 'dash' }
        : { width: 1.5 },
      marker: isCurrent ? { size: 7, color: COLOR_CURRENT, symbol: 'star' } : undefined,
      opacity: isCurrent ? 1.0 : isCovid ? 0.85 : 0.65,
      hovertemplate: `Day %{x}<br>${label}: %{y:.2%}<extra></extra>`,
    });
  });

  const layout: any = {
    title: { text: title, font: { size: 13 } },
    xaxis: { title: xTitle, tickfont: { size: 10 } },
    yaxis: { title: yTitle, tickformat: '.0%', tickfont: { size: 10 } },
    hovermode: 'x unified',
    shapes: [{ type: 'line', x0: 0, x1: 1, xref: 'paper', y0: 1, y1: 1, yref: 'y', line: { dash: 'dot', color: refLineColor, width: 1 } }],
  };

  // applyChartTheme overrides the layout; use the return value
  const fig = applyChartTheme({ layout } as any, theme as any, { chartStyle: 'minimal' }) as any;

  fig.data = data; // re-attach the original data array bypassing any clone dropping

  // Restore settings that applyChartTheme overrides (keep autosize:true — height via wrapper div)
  fig.layout.hovermode = 'x unified';
  fig.layout.margin    = { l: 55, r: 220, t: 46, b: 46 };
  fig.layout.legend    = { ...fig.layout.legend, orientation: 'v', x: 1.02, y: 1, xanchor: 'left', yanchor: 'top', font: { ...fig.layout.legend?.font, size: 9 } };

  return fig;
}

function buildBarChart(
  labels: string[],
  values: number[],
  colors: string[],
  hoverLabel: string,
  height: number,
  theme: string,
  lang: Lang,
) {
  const displayLabels = lang === 'ko' ? labels.map(l => CONFLICT_NAMES_KO[l] ?? l) : labels;
  const data: any[] = [{
    type: 'bar', x: displayLabels, y: values,
    marker: { color: colors },
    hovertemplate: `%{x}<br>${hoverLabel}: %{y}<extra></extra>`,
  }];
  const layout: any = {
    xaxis: { tickangle: -45, tickfont: { size: 8 } },
    yaxis: { tickfont: { size: 9 } },
    showlegend: false,
  };

  // applyChartTheme overrides the layout; use the return value
  const fig = applyChartTheme({ layout } as any, theme as any, { chartStyle: 'minimal' }) as any;

  fig.data = data; // re-attach the original data array bypassing any clone dropping

  // Restore settings that applyChartTheme overrides (keep autosize:true — height via wrapper div)
  fig.layout.margin     = { l: 35, r: 10, t: 10, b: 110 };
  fig.layout.showlegend = false;

  return fig;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function WartimePlot({
  plotId,
  figure,
  height,
  theme,
  lang,
}: {
  plotId: string;
  figure: WartimeFigure;
  height: string;
  theme: string;
  lang: Lang;
}) {
  const plotRef = useRef<HTMLDivElement>(null);
  const [plotError, setPlotError] = useState<string | null>(null);
  const [isRendering, setIsRendering] = useState(true);

  useEffect(() => {
    let cancelled = false;
    let resizeObserver: ResizeObserver | null = null;
    let plotlyModule: any = null;

    const renderPlot = async () => {
      if (!plotRef.current) return;
      setIsRendering(true);
      setPlotError(null);

      try {
        plotlyModule = (await import('plotly.js-dist-min')).default;
        if (cancelled || !plotRef.current) return;

        const data = clonePlotValue(figure.data ?? []);
        const layout = stripUndefinedDeep(clonePlotValue(figure.layout ?? {}));
        layout.autosize = true;
        layout.uirevision = `${plotId}-${theme}-${lang}`;

        try {
          plotlyModule.purge(plotRef.current);
        } catch {}

        await plotlyModule.react(
          plotRef.current,
          stripUndefinedDeep(data),
          layout,
          { responsive: true, displayModeBar: false, displaylogo: false },
        );

        if (cancelled || !plotRef.current) return;

        if (typeof ResizeObserver !== 'undefined') {
          resizeObserver = new ResizeObserver(() => {
            if (!plotRef.current || !plotRef.current.isConnected) return;
            try {
              plotlyModule.Plots.resize(plotRef.current);
            } catch {}
          });
          resizeObserver.observe(plotRef.current);
        }
      } catch (error) {
        if (!cancelled) {
          setPlotError(error instanceof Error ? error.message : 'Chart render failed.');
        }
      } finally {
        if (!cancelled) {
          setIsRendering(false);
        }
      }
    };

    renderPlot();

    return () => {
      cancelled = true;
      resizeObserver?.disconnect();
      if (plotRef.current && plotlyModule) {
        try {
          plotlyModule.purge(plotRef.current);
        } catch {}
      }
    };
  }, [figure, plotId, theme, lang]);

  return (
    <div className="relative" style={{ height }}>
      <div ref={plotRef} className="h-full w-full" />
      {isRendering && !plotError && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/70">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-sky-500/50" />
            <span className="text-[11px] text-muted-foreground/50 tracking-widest uppercase">Loading Chart</span>
          </div>
        </div>
      )}
      {plotError && (
        <div className="absolute inset-0 flex items-center justify-center text-center px-4">
          <div className="flex flex-col items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500/70" />
            <div className="text-[11px] text-muted-foreground">{plotError}</div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="panel-card p-4 flex flex-col gap-1">
      <div className="stat-label">{label}</div>
      <div className="text-xl font-semibold text-foreground tabular-nums">{value}</div>
      {sub && <div className="text-[11px] text-muted-foreground/60">{sub}</div>}
    </div>
  );
}

type TShape = typeof T[keyof typeof T];

function SpxStatsTable({ stats, t, lang }: { stats: SpxStat[]; t: TShape; lang: Lang }) {
  const nameOf = (n: string) => lang === 'ko' ? (CONFLICT_NAMES_KO[n] ?? n) : n;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[11px] border-collapse">
        <thead>
          <tr className="border-b border-border/60">
            <th className="text-left py-2 pr-3 text-muted-foreground/70 font-medium whitespace-nowrap">{t.thConflict}</th>
            <th className="text-right py-2 px-2 text-muted-foreground/70 font-medium whitespace-nowrap">{t.thStart}</th>
            <th className="text-right py-2 px-2 text-muted-foreground/70 font-medium whitespace-nowrap">{t.thMdd}</th>
            <th className="text-right py-2 px-2 text-muted-foreground/70 font-medium whitespace-nowrap">{t.thDaysToLow}</th>
            <th className="text-right py-2 px-2 text-muted-foreground/70 font-medium whitespace-nowrap">{t.thRecovery}</th>
            <th className="text-right py-2 pl-2 text-muted-foreground/70 font-medium whitespace-nowrap">{t.thFinalRet}</th>
          </tr>
        </thead>
        <tbody>
          {stats.map((r, i) => {
            const isCurrent = r.conflict.includes('Current');
            const isCovid   = r.conflict.includes('2020');
            return (
              <tr key={i} className={`border-b border-border/30 transition-colors hover:bg-foreground/[0.02] ${isCurrent ? 'bg-red-500/[0.06]' : isCovid ? 'bg-amber-500/[0.04]' : ''}`}>
                <td className={`py-1.5 pr-3 ${isCurrent ? 'text-red-500 font-medium' : isCovid ? 'text-amber-500' : 'text-foreground'}`}>{nameOf(r.conflict)}</td>
                <td className="py-1.5 px-2 text-right text-muted-foreground tabular-nums">{r.start_date}</td>
                <td className={`py-1.5 px-2 text-right tabular-nums ${r.mdd < -0.15 ? 'text-red-500' : r.mdd < -0.07 ? 'text-amber-500' : 'text-emerald-500'}`}>{absLow(r.mdd)}</td>
                <td className="py-1.5 px-2 text-right text-muted-foreground tabular-nums">{r.days_to_bottom}d</td>
                <td className="py-1.5 px-2 text-right text-muted-foreground tabular-nums">
                  {r.recovery_days !== null ? `${r.recovery_days}d` : t.notRecovered}
                </td>
                <td className={`py-1.5 pl-2 text-right tabular-nums ${r.final_return >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>{pct(r.final_return)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function CommodityStatsTable({ stats, t, lang }: { stats: CommodityStat[]; t: TShape; lang: Lang }) {
  const nameOf = (n: string) => lang === 'ko' ? (CONFLICT_NAMES_KO[n] ?? n) : n;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[11px] border-collapse">
        <thead>
          <tr className="border-b border-border/60">
            <th className="text-left py-2 pr-3 text-muted-foreground/70 font-medium whitespace-nowrap">{t.thConflict}</th>
            <th className="text-right py-2 px-2 text-muted-foreground/70 font-medium whitespace-nowrap">{t.thStart}</th>
            <th className="text-right py-2 px-2 text-muted-foreground/70 font-medium whitespace-nowrap">{t.thPeakGain}</th>
            <th className="text-right py-2 px-2 text-muted-foreground/70 font-medium whitespace-nowrap">{t.thDaysToPeak}</th>
            <th className="text-right py-2 px-2 text-muted-foreground/70 font-medium whitespace-nowrap">{t.thMddFromPeak}</th>
            <th className="text-right py-2 pl-2 text-muted-foreground/70 font-medium whitespace-nowrap">{t.thFinalRet}</th>
          </tr>
        </thead>
        <tbody>
          {stats.map((r, i) => {
            const isCurrent = r.conflict.includes('Current');
            const isCovid   = r.conflict.includes('2020');
            return (
              <tr key={i} className={`border-b border-border/30 transition-colors hover:bg-foreground/[0.02] ${isCurrent ? 'bg-red-500/[0.06]' : isCovid ? 'bg-amber-500/[0.04]' : ''}`}>
                <td className={`py-1.5 pr-3 ${isCurrent ? 'text-red-500 font-medium' : isCovid ? 'text-amber-500' : 'text-foreground'}`}>{nameOf(r.conflict)}</td>
                <td className="py-1.5 px-2 text-right text-muted-foreground tabular-nums">{r.start_date}</td>
                <td className={`py-1.5 px-2 text-right tabular-nums ${r.peak_gain >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>{pct(r.peak_gain)}</td>
                <td className="py-1.5 px-2 text-right text-muted-foreground tabular-nums">{r.days_to_peak}d</td>
                <td className="py-1.5 px-2 text-right text-amber-500 tabular-nums">{absLow(r.mdd)}</td>
                <td className={`py-1.5 pl-2 text-right tabular-nums ${r.final_return >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>{pct(r.final_return)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function WartimePage() {
  const { theme } = useTheme();
  const [lang, setLang] = useState<Lang>('en');
  const t = T[lang];

  const { data, isLoading, isError } = useQuery<WartimeData>({
    queryKey: ['wartime'],
    queryFn: () => apiFetchJson('/api/wartime/data'),
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  // ── Charts (re-build on data, theme, or lang change) ─────────────────────
  const spxLineChart = useMemo(() => {
    if (!data) return null;
    return buildLineChart(data.spx.rebased, t.spxChartTitle, t.spxYAxis, t.spxXAxis, theme, lang);
  }, [data, theme, lang]);

  const goldLineChart = useMemo(() => {
    if (!data) return null;
    return buildLineChart(data.gold.rebased, t.goldChartTitle, t.goldYAxis, t.spxXAxis, theme, lang);
  }, [data, theme, lang]);

  const oilLineChart = useMemo(() => {
    if (!data) return null;
    return buildLineChart(data.oil.rebased, t.oilChartTitle, t.oilYAxis, t.spxXAxis, theme, lang);
  }, [data, theme, lang]);

  const mddBarChart = useMemo(() => {
    if (!data) return null;
    const hist = data.spx.stats.filter(r => !r.conflict.includes('Current'));
    return buildBarChart(hist.map(r => r.conflict), hist.map(r => r.mdd * 100),
      hist.map(r => r.mdd < -0.15 ? '#EF4444' : '#F97316'), t.barMddHover, 260, theme, lang);
  }, [data, theme, lang]);

  const bottomBarChart = useMemo(() => {
    if (!data) return null;
    const hist = data.spx.stats.filter(r => !r.conflict.includes('Current'));
    return buildBarChart(hist.map(r => r.conflict), hist.map(r => r.days_to_bottom),
      hist.map(() => '#6366F1'), t.barBottomHover, 260, theme, lang);
  }, [data, theme, lang]);

  const recoveryBarChart = useMemo(() => {
    if (!data) return null;
    const hist = data.spx.stats.filter(r => !r.conflict.includes('Current'));
    return buildBarChart(hist.map(r => r.conflict), hist.map(r => r.recovery_days ?? 200),
      hist.map(r => r.recovery_days === null ? '#9CA3AF' : '#10B981'), t.barRecoveryHover, 260, theme, lang);
  }, [data, theme, lang]);

  // ── Language toggle button ────────────────────────────────────────────────
  const LangToggle = (
    <button
      onClick={() => setLang(l => l === 'en' ? 'ko' : 'en')}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border/60 text-[11px] font-medium text-muted-foreground hover:text-foreground hover:border-border transition-colors bg-background"
    >
      <span className="text-base leading-none">🌐</span>
      {t.langToggle}
    </button>
  );

  // ── Loading / error ───────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-8 h-8 animate-spin text-sky-500/60" />
            <span className="text-[12px] text-muted-foreground/60 tracking-widest uppercase">{t.loading}</span>
          </div>
        </div>
      </AppShell>
    );
  }

  if (isError || !data) {
    return (
      <AppShell>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="flex flex-col items-center gap-3 text-center">
            <AlertTriangle className="w-8 h-8 text-amber-500/60" />
            <p className="text-[13px] text-muted-foreground">{t.loadError}</p>
          </div>
        </div>
      </AppShell>
    );
  }

  const { current, summary } = data;

  return (
    <AppShell>
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-6 space-y-10">

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-foreground">{t.title}</h1>
            <p className="text-[12px] text-muted-foreground mt-1">{t.subtitle}</p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {LangToggle}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-red-500/30 bg-red-500/[0.06]">
              <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              <span className="text-[11px] font-medium text-red-500">{t.analysisDate}</span>
            </div>
          </div>
        </div>

        {/* ── Commentary ─────────────────────────────────────────────────── */}
        <div className="panel-card p-5 border-l-4 border-sky-500/50">
          <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground/50 mb-2">{t.commentaryLabel}</div>
          <p className="text-[13px] text-foreground/90 leading-relaxed">
            {t.commentaryText[0]}
            {t.commentaryText[1]}<strong>{t.commentaryText[2]}</strong>{t.commentaryText[3]}
            {t.commentaryText[4]}<strong>{t.commentaryText[5]}</strong>{t.commentaryText[6]}<strong>{t.commentaryText[7]}</strong>{t.commentaryText[8]}
            {t.commentaryText[9]}<strong>{t.commentaryText[10]}</strong>{t.commentaryText[11]}<strong>{t.commentaryText[12]}</strong>{t.commentaryText[13]}
            {t.commentaryText[14]}
            {t.commentaryText[15]}
            {t.commentaryText[16]}
          </p>
        </div>

        {/* ══════════════════════════════════════════════════════════════════ */}
        {/* SPX                                                               */}
        {/* ══════════════════════════════════════════════════════════════════ */}
        <section className="space-y-5">
          <h2 className="text-[15px] font-semibold text-foreground flex items-center gap-2">
            <span className="text-sky-400">{t.spxTitle}</span>
            <span className="text-muted-foreground font-normal text-[13px]">{t.spxSubtitle}</span>
          </h2>

          <div className="panel-card p-4">
            {spxLineChart && <WartimePlot plotId="spx-line" figure={spxLineChart} height="460px" theme={theme} lang={lang} />}
            <p className="text-[11px] text-muted-foreground/60 mt-1 ml-1">{t.spxCovid}</p>
          </div>

          <div className="panel-card p-4">
            <div className="stat-label mb-3">{t.spxTableLabel}</div>
            <SpxStatsTable stats={data.spx.stats} t={t} lang={lang} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="panel-card p-4">
              <div className="stat-label mb-2">{t.barMddTitle}</div>
              {mddBarChart && <WartimePlot plotId="spx-mdd-bar" figure={mddBarChart} height="260px" theme={theme} lang={lang} />}
            </div>
            <div className="panel-card p-4">
              <div className="stat-label mb-2">{t.barBottomTitle}</div>
              {bottomBarChart && <WartimePlot plotId="spx-bottom-bar" figure={bottomBarChart} height="260px" theme={theme} lang={lang} />}
            </div>
            <div className="panel-card p-4">
              <div className="stat-label mb-2">{t.barRecoveryTitle}</div>
              {recoveryBarChart && <WartimePlot plotId="spx-recovery-bar" figure={recoveryBarChart} height="260px" theme={theme} lang={lang} />}
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard label={t.avgMdd}       value={absLow(summary.avg_mdd)}                                                                      sub={t.avgMddSub} />
            <StatCard label={t.avgBottom}    value={summary.avg_bottom_days   !== null ? `${summary.avg_bottom_days.toFixed(0)}d`   : 'N/A'}      sub={t.avgBottomSub} />
            <StatCard label={t.avgRecovery}  value={summary.avg_recovery_days !== null ? `${summary.avg_recovery_days.toFixed(0)}d` : 'N/A'}      sub={t.avgRecoverySub} />
            <StatCard label={t.recoveryRate} value={summary.recovery_rate     !== null ? `${(summary.recovery_rate * 100).toFixed(0)}%` : 'N/A'} sub={t.recoveryRateSub} />
          </div>
        </section>

        {/* ══════════════════════════════════════════════════════════════════ */}
        {/* GOLD                                                              */}
        {/* ══════════════════════════════════════════════════════════════════ */}
        <section className="space-y-5">
          <h2 className="text-[15px] font-semibold text-foreground flex items-center gap-2">
            <span style={{ color: COLOR_GOLD }}>{t.goldTitle}</span>
            <span className="text-muted-foreground font-normal text-[13px]">{t.goldSubtitle}</span>
          </h2>
          <div className="panel-card p-4">
            {goldLineChart && <WartimePlot plotId="gold-line" figure={goldLineChart} height="460px" theme={theme} lang={lang} />}
          </div>
          <div className="panel-card p-4">
            <div className="stat-label mb-3">{t.goldTableLabel}</div>
            <CommodityStatsTable stats={data.gold.stats} t={t} lang={lang} />
            <p className="text-[11px] text-muted-foreground/50 mt-3">{t.goldNote}</p>
          </div>
        </section>

        {/* ══════════════════════════════════════════════════════════════════ */}
        {/* WTI                                                               */}
        {/* ══════════════════════════════════════════════════════════════════ */}
        <section className="space-y-5">
          <h2 className="text-[15px] font-semibold text-foreground flex items-center gap-2">
            <span style={{ color: COLOR_OIL }}>{t.oilTitle}</span>
            <span className="text-muted-foreground font-normal text-[13px]">{t.oilSubtitle}</span>
          </h2>
          <div className="panel-card p-4">
            {oilLineChart && <WartimePlot plotId="oil-line" figure={oilLineChart} height="460px" theme={theme} lang={lang} />}
          </div>
          <div className="panel-card p-4">
            <div className="stat-label mb-3">{t.oilTableLabel}</div>
            <CommodityStatsTable stats={data.oil.stats} t={t} lang={lang} />
          </div>
          <div className="panel-card p-4 border-amber-500/30 bg-amber-500/[0.05] flex gap-3">
            <span className="text-lg shrink-0">⚡</span>
            <p className="text-[12px] text-foreground/80 leading-relaxed">
              <strong>{t.shaleTitle}</strong> {t.shaleText}
            </p>
          </div>
        </section>

        {/* ── EM table ───────────────────────────────────────────────────── */}
        <section className="space-y-3">
          <h2 className="text-[15px] font-semibold text-foreground">{t.emTitle}</h2>
          <p className="text-[12px] text-muted-foreground">{t.emSubtitle}</p>
          <div className="panel-card overflow-x-auto">
            <table className="w-full text-[12px] border-collapse">
              <thead>
                <tr className="border-b border-border/60">
                  <th className="text-left py-2.5 px-4 text-muted-foreground/70 font-medium">{t.emThCountry}</th>
                  <th className="text-left py-2.5 px-4 text-muted-foreground/70 font-medium">{t.emThStance}</th>
                  <th className="text-left py-2.5 px-4 text-muted-foreground/70 font-medium">{t.emThAssessment}</th>
                </tr>
              </thead>
              <tbody>
                {t.emRows.map((row, i) => (
                  <tr key={i} className="border-b border-border/30 hover:bg-foreground/[0.02]">
                    <td className="py-2.5 px-4 font-medium text-foreground">{row.flag} {row.country}</td>
                    <td className="py-2.5 px-4">
                      <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded ${
                        row.stance === 'Vulnerable'  ? 'bg-red-500/10 text-red-500' :
                        row.stance === 'Buffered'    ? 'bg-amber-500/10 text-amber-500' :
                        'bg-emerald-500/10 text-emerald-600'
                      }`}>
                        {row.stanceKo}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 text-muted-foreground">{row.desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── Iran Live Snapshot ─────────────────────────────────────────── */}
        <section className="space-y-3">
          <h2 className="text-[15px] font-semibold text-foreground flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            {t.iranTitle}
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <StatCard label={t.cardDaysElapsed} value={`${current.spx_days_elapsed}d`}                                          sub={t.cardDaysElapsedSub} />
            <StatCard label={t.cardSpxReturn}   value={pct(current.spx_return)}                                                  sub={t.cardSpxReturnSub} />
            <StatCard label={t.cardSpxLow}      value={current.spx_low !== null ? absLow(current.spx_low) : 'N/A'}               sub={t.cardSpxLowSub} />
            <StatCard label={t.cardGoldReturn}  value={pct(current.gold_return)}                                                 sub={t.cardGoldReturnSub} />
            <StatCard label={t.cardOilReturn}   value={pct(current.oil_return)}                                                  sub={t.cardOilReturnSub} />
          </div>
        </section>

        {/* ── Scenarios ───────────────────────────────────────────────────── */}
        <section className="space-y-3">
          <h2 className="text-[15px] font-semibold text-foreground">{t.scenariosTitle}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="panel-card p-5 border-emerald-500/30 bg-emerald-500/[0.04]">
              <div className="text-[10px] font-mono uppercase tracking-widest text-emerald-600 dark:text-emerald-400 mb-2">{t.bullLabel}</div>
              <div className="text-[12px] text-muted-foreground/70 mb-3">{t.bullAnalogues}</div>
              <div className="space-y-1.5 text-[13px] text-foreground/90">
                <div className="flex justify-between"><span>{t.rowExpectedDrawdown}</span><span className="text-amber-600 dark:text-amber-400 font-medium">{t.bullDrawdown}</span></div>
                <div className="flex justify-between"><span>{t.rowRecoveryTimeline}</span><span className="text-emerald-600 dark:text-emerald-400 font-medium">{t.bullRecovery}</span></div>
                <div className="flex justify-between"><span>{t.row200dReturn}</span><span className="text-emerald-600 dark:text-emerald-400 font-medium">{t.bull200d}</span></div>
              </div>
              <p className="text-[12px] text-muted-foreground/60 mt-3 leading-relaxed">{t.bullText}</p>
            </div>
            <div className="panel-card p-5 border-red-500/30 bg-red-500/[0.04]">
              <div className="text-[10px] font-mono uppercase tracking-widest text-red-500 mb-2">{t.bearLabel}</div>
              <div className="text-[12px] text-muted-foreground/70 mb-3">{t.bearAnalogues}</div>
              <div className="space-y-1.5 text-[13px] text-foreground/90">
                <div className="flex justify-between"><span>{t.rowExpectedDrawdown}</span><span className="text-red-500 font-medium">{t.bearDrawdown}</span></div>
                <div className="flex justify-between"><span>{t.rowRecoveryTimeline}</span><span className="text-amber-600 dark:text-amber-400 font-medium">{t.bearRecovery}</span></div>
                <div className="flex justify-between"><span>{t.row200dReturn}</span><span className="text-amber-600 dark:text-amber-400 font-medium">{t.bear200d}</span></div>
              </div>
              <p className="text-[12px] text-muted-foreground/60 mt-3 leading-relaxed">{t.bearText}</p>
            </div>
          </div>
        </section>

        {/* ── COVID Warning ───────────────────────────────────────────────── */}
        <section>
          <div className="panel-card p-5 border-amber-500/40 bg-amber-500/[0.05] flex gap-4">
            <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
            <div className="space-y-2">
              <div className="text-[13px] font-semibold text-amber-600 dark:text-amber-400">{t.covidTitle}</div>
              <p className="text-[12px] text-foreground/80 leading-relaxed">
                {lang === 'ko'
                  ? <>{t.covidText1}<strong>{t.covidCaution}</strong>.</>
                  : <>{t.covidText1}</>
                }
              </p>
              <p className="text-[12px] text-muted-foreground/70">{t.covidText2}</p>
            </div>
          </div>
        </section>

        {/* ── Monitoring table ────────────────────────────────────────────── */}
        <section className="space-y-3">
          <h2 className="text-[15px] font-semibold text-foreground">{t.monitoringTitle}</h2>
          <div className="panel-card overflow-x-auto">
            <table className="w-full text-[12px] border-collapse">
              <thead>
                <tr className="border-b border-border/60">
                  <th className="text-left py-2.5 px-4 text-muted-foreground/70 font-medium">{t.monThMetric}</th>
                  <th className="text-left py-2.5 px-4 text-emerald-600 dark:text-emerald-400 font-medium">{t.monThBull}</th>
                  <th className="text-left py-2.5 px-4 text-red-500 font-medium">{t.monThBear}</th>
                </tr>
              </thead>
              <tbody>
                {t.monRows.map((row, i) => (
                  <tr key={i} className="border-b border-border/30 hover:bg-foreground/[0.02]">
                    <td className="py-2.5 px-4 font-medium text-foreground">{row.metric}</td>
                    <td className="py-2.5 px-4 text-emerald-600 dark:text-emerald-400">{row.bull}</td>
                    <td className="py-2.5 px-4 text-red-500">{row.bear}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[11px] text-muted-foreground/50 px-1">{t.disclaimer}</p>
        </section>

      </div>
    </AppShell>
  );
}
