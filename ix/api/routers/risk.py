from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from ix.web.pages.risk import analytics
import plotly.io as pio

router = APIRouter()

@router.get("/risk/html", response_class=HTMLResponse)
async def get_risk_report():
    """
    Returns the Risk Management Dashboard as a static HTML report.
    """
    try:
        # Get data and figures
        metrics = analytics.calculate_risk_metrics()
        oecd_fig = analytics.create_oecd_chart()
        gauge_data = analytics.get_gauge_charts_data()
        
        if not metrics:
             return HTMLResponse(content="<html><body><h1>No Data Available</h1></body></html>", status_code=404)

        # Generate HTML components
        
        # 1. OECD Chart
        oecd_html = pio.to_html(oecd_fig, full_html=False, include_plotlyjs='cdn')
        
        # 2. Key Metrics Cards
        alert = metrics['alert']
        positive = metrics['positive']
        oecd_metric = metrics['oecd']
        
        # Styles
        style = """
        <style>
            body { font-family: 'Inter', sans-serif; background-color: #0f172a; color: #ffffff; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .card { background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(71, 85, 105, 0.5); border-radius: 8px; padding: 20px; margin-bottom: 20px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom: 20px; }
            .metric-box { background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%); padding: 15px; border-radius: 8px; border: 1px solid rgba(71, 85, 105, 0.5); }
            .label { font-size: 0.8rem; font-weight: 600; color: #94a3b8; display: block; margin-bottom: 5px; }
            .value { font-size: 1.5rem; font-weight: 700; color: #ffffff; }
            .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; display: inline-block; margin-left: 8px; }
            
            .alert-box { padding: 15px; border-radius: 8px; border-left: 4px solid; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
            
            h1 { font-size: 2rem; font-weight: 700; margin-bottom: 30px; border-bottom: 1px solid #334155; padding-bottom: 15px; }
            h2 { font-size: 1.5rem; font-weight: 600; margin-bottom: 15px; color: #e2e8f0; }
        </style>
        """
        
        # Alert Component
        alert_bg = "rgba(239, 68, 68, 0.1)" if alert['color'] == "#dc2626" else "rgba(16, 185, 129, 0.1)"
        if alert['level'] == 'Warning': alert_bg = "rgba(245, 158, 11, 0.1)"
        if alert['level'] == 'Normal': alert_bg = "rgba(16, 185, 129, 0.1)"
        
        alert_html = f"""
        <div class="alert-box" style="background: {alert_bg}; border-color: {alert['color']};">
            <div>
                <span style="font-size: 1.2rem; margin-right: 10px;">{alert['text']}</span>
                <span style="color: {alert['color']}; font-weight: 600;">Current Sigma: {alert['sigma']:.2f}σ</span>
            </div>
            <span class="badge" style="background: {alert['color']}; color: white;">{alert['badge']}</span>
        </div>
        """
        
        # Metrics Grid
        metrics_html = f"""
        <div class="grid">
            <div class="metric-box">
                <span class="label">📅 Latest Update</span>
                <span class="value">{metrics['latest_date'].strftime('%Y-%m-%d')}</span>
            </div>
            <div class="metric-box">
                <span class="label">📈 Total Indices</span>
                <span class="value">{positive['total']}</span>
            </div>
            <div class="metric-box">
                <span class="label">📊 Positive Today</span>
                <div style="display: flex; align-items: center;">
                    <span class="value">{positive['count']}/{positive['total']}</span>
                    <span class="badge" style="background: {positive['color']}; color: white;">{positive['state']}</span>
                </div>
            </div>
             <div class="metric-box">
                <span class="label">🌍 OECD CLI</span>
                <div style="display: flex; align-items: center;">
                    <span class="value">{oecd_metric['pct']:.1f}%</span>
                    <span class="badge" style="background: {oecd_metric['color']}; color: white;">{oecd_metric['state']}</span>
                </div>
            </div>
        </div>
        """
        
        # Gauges
        gauges_html = '<div style="display: flex; flex-wrap: wrap; gap: 20px;">'
        for item in gauge_data:
            chart_html = pio.to_html(item['figure'], full_html=False, include_plotlyjs=False)
            gauges_html += f'<div style="flex: 1 1 45%; min-width: 400px; background: rgba(30, 41, 59, 0.6); border-radius: 12px; border: 1px solid rgba(71, 85, 105, 0.3); padding: 10px;">{chart_html}</div>'
        gauges_html += '</div>'

        # Full Page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Risk Management Report</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
            {style}
        </head>
        <body>
            <div class="container">
                <!-- Header -->
                <h1 style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.2rem; margin-bottom: 0.1rem; text-align: center; border-bottom: none;">📈 위험자산 리스크관리 프로세스 대시보드</h1>
                <p style="text-align: center; color: #a0aec0; margin-bottom: 2rem; font-size: 0.9rem;">흥국생명 자산운용본부 투자기획팀</p>
                
                <!-- Background -->
                <h3 style="border-bottom: 2px solid #475569; padding-bottom: 0.3rem; margin-top: 2rem; color: white; font-size: 1.3rem;">📋 배경 및 목적</h3>
                <p style="color: #cbd5e0; line-height: 1.6; font-size: 0.95rem;">
                    - 크레딧 및 주식자산의 리스크 요인을 사전 식별하기 위한 핵심 시장지표 모니터링.<br>
                    - 지표별 변동을 정량화하여 위험 수준을 단계별(Yellow/Red)로 구분하여 자산배분 및 한도 관리 체계의 조기경보 기능을 강화.
                </p>

                <!-- Implications -->
                <h3 style="border-bottom: 2px solid #475569; padding-bottom: 0.3rem; margin-top: 2rem; color: white; font-size: 1.3rem;">💡 시사점 및 리스크 가이드라인</h3>
                <div style="display: flex; gap: 20px; margin-bottom: 2rem; flex-wrap: wrap;">
                    <div style="flex: 2; min-width: 300px;">
                        <h4 style="color: white; margin-bottom: 10px; font-size: 1.1rem;">시사점:</h4>
                        <p style="color: #cbd5e0; margin-bottom: 5px;">• 리스크 조기감지: 통계적 유의성 기반 계량적 접근</p>
                        <p style="color: #cbd5e0; margin-bottom: 5px;">• 자산배분 최적화: 정량화된 지표 기반 리밸런싱</p>
                    </div>
                    <div style="flex: 1; background: rgba(245, 158, 11, 0.15); border-left: 4px solid #f59e0b; padding: 12px; border-radius: 8px; min-width: 200px; border: 1px solid rgba(245, 158, 11, 0.3);">
                        <p style="color: #92400e; font-weight: 600; margin-bottom: 8px; font-size: 0.9rem;">💳 크레딧 자산</p>
                        <p style="color: white; font-size: 0.8rem; margin-bottom: 4px; font-weight: 600;">🟡 Yellow: 신규매수금지</p>
                        <p style="color: white; font-size: 0.8rem; margin: 0; font-weight: 600;">🔴 Red: 현금화 고민</p>
                    </div>
                    <div style="flex: 1; background: rgba(239, 68, 68, 0.15); border-left: 4px solid #ef4444; padding: 12px; border-radius: 8px; min-width: 200px; border: 1px solid rgba(239, 68, 68, 0.3);">
                        <p style="color: #991b1b; font-weight: 600; margin-bottom: 8px; font-size: 0.9rem;">📈 주식 자산</p>
                        <p style="color: white; font-size: 0.8rem; margin-bottom: 4px; font-weight: 600;">🟡 Yellow: 10%이상 현금화</p>
                        <p style="color: white; font-size: 0.8rem; margin: 0; font-weight: 600;">🔴 Red: 40%이상 현금화</p>
                    </div>
                </div>

                <!-- Metrics Header -->
                <h3 style="border-bottom: 2px solid #475569; padding-bottom: 0.3rem; margin-top: 2rem; color: white; font-size: 1.3rem;">📊 종합 리스크 지표</h3>
                
                {alert_html}
                {metrics_html}
                
                <!-- OECD -->
                <h3 style="border-bottom: 2px solid #475569; padding-bottom: 0.3rem; margin-top: 2rem; color: white; font-size: 1.3rem;">📈 OECD CLI Analysis</h3>
                <div class="card">
                    {oecd_html}
                </div>
                
                <!-- Gauges Section -->
                <h3 style="border-bottom: 2px solid #475569; padding-bottom: 0.3rem; margin-top: 2rem; color: white; font-size: 1.3rem;">🎯 개별 지표 상세 분석</h3>
                
                <!-- Indicator Explanations -->
                <div style="background: rgba(30, 41, 59, 0.7); padding: 16px; border-radius: 12px; border: 1px solid rgba(71, 85, 105, 0.5); margin-bottom: 1rem;">
                    <h4 style="color: white; margin-bottom: 12px; font-size: 1.1rem;">📊 지표별 의미</h4>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; font-size: 0.9rem; color: #cbd5e0;">
                        <div>
                            <p style="margin-bottom: 6px;"><b>📈 코스피:</b> 한국 주식시장 대표지수 (5주 하락율)</p>
                            <p style="margin-bottom: 6px;"><b>🇺🇸 S&P 500:</b> 미국 주식시장 대표지수 (5주 하락율)</p>
                            <p style="margin-bottom: 6px;"><b>🏦 한국CD91:</b> 한국 91일 만기 양도성예금증서 금리 (5주 상승폭)</p>
                            <p style="margin-bottom: 6px;"><b>📊 한국 10년:</b> 한국 10년 국채 금리 (5주 상승폭)</p>
                        </div>
                        <div>
                            <p style="margin-bottom: 6px;"><b>🇺🇸 미국 10년:</b> 미국 10년 국채 금리 (5주 상승폭)</p>
                            <p style="margin-bottom: 6px;"><b>💱 미국-한국 10년:</b> 미국-한국 10년 국채 금리차 (5주 상승폭)</p>
                            <p style="margin-bottom: 6px;"><b>🏢 한국회사채 스프레드:</b> AA- 등급 회사채와 국채 금리차 (5주 상승폭)</p>
                            <p style="margin-bottom: 0px;"><b>💵 달러-원 환율:</b> USD/KRW 환율 (5주 상승율)</p>
                        </div>
                    </div>
                </div>

                <!-- Gauge Explanations -->
                <div style="background: rgba(30, 41, 59, 0.7); padding: 16px; border-radius: 12px; border: 1px solid rgba(71, 85, 105, 0.5); margin-bottom: 1rem;">
                    <h4 style="color: white; margin-bottom: 12px; font-size: 1.1rem;">📊 게이지 작동 방식</h4>
                    <div style="color: #cbd5e0; font-size: 0.9rem; line-height: 1.5;">
                        <p style="margin-bottom: 8px;"><b>• 통계적 유의성:</b> 현재 값을 3년간 롤링 통계(104주 윈도우)와 비교</p>
                        <p style="margin-bottom: 8px;"><b>• 색상 구분:</b> 빨간색/노란색은 음의 편차, 초록색/파란색은 양의 편차를 나타냄</p>
                        <p style="margin-bottom: 0px;"><b>• 상태 배지:</b> 우상단 모서리에 현재 통계적 상태(위험, 주의, 중립)를 표시</p>
                    </div>
                </div>

                <!-- Legend -->
                <div style="background: rgba(30, 41, 59, 0.7); padding: 8px; border-radius: 12px; border: 1px solid rgba(71, 85, 105, 0.5); margin-bottom: 1rem; display: flex; justify-content: center; flex-wrap: wrap; gap: 6px;">
                    <span style="padding: 6px 12px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; color: white; background: #dc2626; margin: 2px;">위험 -</span>
                    <span style="padding: 6px 12px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; color: white; background: #f59e0b; margin: 2px;">주의 -</span>
                    <span style="padding: 6px 12px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; color: white; background: #6b7280; margin: 2px;">중립 -</span>
                    <span style="padding: 6px 12px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; color: white; background: #10b981; margin: 2px;">중립 +</span>
                    <span style="padding: 6px 12px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; color: white; background: #3b82f6; margin: 2px;">주의 +</span>
                    <span style="padding: 6px 12px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; color: white; background: #1d4ed8; margin: 2px;">위험 +</span>
                </div>

                <div class="card">
                    {gauges_html}
                </div>
                
                <hr style="border-color: #475569; margin-top: 2rem; margin-bottom: 2rem;">
                <div style="background: rgba(30, 41, 59, 0.3); border-radius: 8px; padding: 16px; text-align: center; border-top: 1px solid #475569;">
                    <p style="color: #94a3b8; font-size: 0.875rem; font-weight: 500; margin-bottom: 0.25rem;">
                        📊 Financial Index Dashboard • Real-time analysis with statistical significance indicators
                    </p>
                    <p style="color: #94a3b8; font-size: 0.875rem; font-weight: 500; margin: 0;">
                        Data source: RawData.xlsx • Updated automatically • Built by 흥국생명 자산운용본부 투자기획팀
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
