"""Streamlit-дашборд для ВКР: выбросы, Бурятия и Забайкалье, 2019–2025."""
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title='Мониторинг выбросов | Бурятия и Забайкалье',
                   page_icon='🌿',layout='wide')
COLORS = ['#2dd4bf','#f59e0b','#60a5fa','#a78bfa','#fb7185','#94a3b8','#34d399']
REGIONS = ['Республика Бурятия','Забайкальский край']
OUT = Path(__file__).resolve().parent

st.markdown('''<style>
.block-container {padding-top:1.6rem;max-width:1300px}
h1 {font-size:2rem !important;letter-spacing:-.04em}
[data-testid="stMetric"] {background:rgba(120,150,160,.07);border:1px solid rgba(120,150,160,.18);border-radius:12px;padding:15px}
[data-testid="stMetricLabel"] {font-size:.9rem}
</style>''', unsafe_allow_html=True)

@st.cache_data
def load():
    names=['yearly','municipalities','industries','pollutants','cleaning','transport','validation']
    return {name:pd.read_csv(OUT/f'{name}.csv',dtype={'oktmo':str,'okved':str})
            for name in names}

try:
    d=load()
except FileNotFoundError:
    st.error('Нет подготовленных CSV. Сначала запусти подготовку данных в Colab.')
    st.stop()

st.title('Мониторинг выбросов загрязняющих веществ')
st.caption('Республика Бурятия · Забайкальский край  |  2019–2025  |  Росприроднадзор, форма 2-ТП (воздух) и оценки транспорта')

with st.sidebar:
    st.header('Фильтры')
    regsel=st.selectbox('Регион',['Оба региона']+REGIONS)
    region_list=REGIONS if regsel=='Оба региона' else [regsel]
    period=st.select_slider('Период для графиков',options=list(range(2019,2026)),value=(2019,2025))
    year=st.selectbox('Год для детального анализа',list(range(2025,2018,-1)))
    st.divider()
    st.caption('Единицы: тыс. тонн для общего объёма, тонн для муниципалитетов, отраслей и веществ.')

y=d['yearly']
yf=y[y.region.isin(region_list)&y.year.between(*period)]
y0=y[(y.year==year)&y.region.isin(region_list)]
y_prev=y[(y.year==year-1)&y.region.isin(region_list)]

def fmt(value,dec=2):
    return f'{value:,.{dec}f}'.replace(',',' ').replace('.',',')

def growth(current,previous):
    if previous<=0: return None
    return (current/previous-1)*100

def fig_style(fig):
    fig.update_layout(margin=dict(l=5,r=5,t=30,b=5),legend_title_text='',
                      hovermode='x unified',height=390)
    return fig

tab1,tab2,tab3,tab4=st.tabs(['Обзор и динамика','Территории','Отрасли (ОКВЭД)','Вещества и очистка'])

with tab1:
    st.subheader(f'Общий мониторинг · {year}')
    total=y0.total_kt.sum(); stationary=y0.stationary_kt.sum(); mobile=y0.mobile_kt.sum()
    delta=growth(total,y_prev.total_kt.sum())
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Все рассматриваемые источники',f'{fmt(total)} тыс. т',
              None if delta is None else f'{delta:+.1f}% к {year-1}')
    c2.metric('Стационарные',f'{fmt(stationary)} тыс. т')
    c3.metric('Автомобильные + ж/д',f'{fmt(mobile)} тыс. т')
    c4.metric('Доля передвижных',f'{fmt(100*mobile/total if total else 0,1)}%')
    st.caption('Совокупный показатель = стационарные + официальная оценка передвижных источников; методики их формирования различаются.')

    a,b=st.columns(2)
    with a:
        st.plotly_chart(fig_style(px.line(yf,x='year',y='stationary_kt',color='region',markers=True,
                    title='Динамика стационарных выбросов, тыс. т',color_discrete_sequence=COLORS,
                    labels={'year':'Год','stationary_kt':'тыс. т','region':'Регион'})),use_container_width=True)
    with b:
        st.plotly_chart(fig_style(px.line(yf,x='year',y='mobile_kt',color='region',markers=True,
                    title='Динамика передвижных выбросов, тыс. т',color_discrete_sequence=COLORS,
                    labels={'year':'Год','mobile_kt':'тыс. т','region':'Регион'})),use_container_width=True)
    src=y0.melt(id_vars=['region'],value_vars=['stationary_kt','car_kt','rail_kt'],
                var_name='source',value_name='value')
    src['source']=src['source'].map({'stationary_kt':'Стационарные','car_kt':'Автомобильные','rail_kt':'Железнодорожные'})
    st.plotly_chart(fig_style(px.bar(src,x='region',y='value',color='source',barmode='stack',
                      title=f'Структура по типам источников, {year} г., тыс. т',
                      color_discrete_sequence=COLORS,labels={'region':'Регион','value':'тыс. т','source':'Источник'})),
                    use_container_width=True)
    st.dataframe(yf[['year','region','stationary_kt','car_kt','rail_kt','mobile_kt','total_kt','total_growth_pct']]
        .sort_values(['year','region'],ascending=[False,True]),hide_index=True,use_container_width=True)

with tab2:
    selected=st.selectbox('Регион для муниципального анализа',region_list,key='territory_region')
    m=d['municipalities']
    mt=m[(m.year==year)&(m.region==selected)].sort_values('stationary_t',ascending=False).copy()
    mt['share_pct']=mt.stationary_t/mt.stationary_t.sum()*100
    top=mt.head(10).iloc[::-1]
    st.subheader(f'Территориальная структура · {selected} · {year}')
    st.plotly_chart(fig_style(px.bar(top,x='stationary_t',y='municipality',orientation='h',
                    title='10 крупнейших записей ОКТМО по стационарным выбросам, тонн',
                    color_discrete_sequence=COLORS,hover_data=['oktmo','share_pct'],
                    labels={'stationary_t':'тонн','municipality':'Муниципалитет'})),
                    use_container_width=True)
    st.metric('Доля TOP-5 муниципальных записей',f'{fmt(mt.head(5).stationary_t.sum()/mt.stationary_t.sum()*100,1)}%')
    st.dataframe(mt[['municipality','oktmo','stationary_t','share_pct']].head(20).round(2),
                 hide_index=True,use_container_width=True)
    st.markdown('**Динамика выбранной территории по ОКТМО**')
    selected_code=st.selectbox('Муниципальное образование',mt['municipality']+' · '+mt['oktmo'].fillna('-'))
    code=selected_code.rsplit(' · ',1)[1]
    def normalize_oktmo(value):
        value=str(value).replace('.0','')
        return value+'000' if len(value)==5 and value.isdigit() else value
    history=m[m.region==selected].copy()
    history['code_normalized']=history.oktmo.map(normalize_oktmo)
    local=history[history.code_normalized==normalize_oktmo(code)]
    local=local[local.year.between(*period)].sort_values('year')
    st.plotly_chart(fig_style(px.line(local,x='year',y='stationary_t',markers=True,
                   title='Выбросы по неизменному ОКТМО, тонн',
                   labels={'year':'Год','stationary_t':'тонн'},color_discrete_sequence=COLORS)),
                   use_container_width=True)
    st.caption('Если территория была преобразована и её ОКТМО изменился, ряд не склеивается автоматически. Строки с одинаковыми названиями и разными кодами не объединяются.')

with tab3:
    selected=st.selectbox('Регион для анализа ОКВЭД',region_list,key='industry_region')
    ind=d['industries']
    current=ind[(ind.year==year)&(ind.region==selected)].sort_values('stationary_t',ascending=False).copy()
    current['share_pct']=current.stationary_t/current.stationary_t.sum()*100
    st.subheader(f'Отраслевая структура · {selected} · {year}')
    top=current.head(10).iloc[::-1]
    st.plotly_chart(fig_style(px.bar(top,x='stationary_t',y='industry',orientation='h',
                    title='TOP-10 видов деятельности по выбросам, тонн',
                    color_discrete_sequence=COLORS,hover_data=['okved','share_pct'],
                    labels={'stationary_t':'тонн','industry':'Отрасль'})),use_container_width=True)
    st.dataframe(current[['okved','industry','stationary_t','share_pct']].head(20).round(2),
                 hide_index=True,use_container_width=True)
    code=st.selectbox('ОКВЭД для анализа по годам',current['okved'].tolist(),
                      format_func=lambda c:f'{c} — '+current.loc[current.okved==c,'industry'].iloc[0])
    trend=ind[(ind.region==selected)&(ind.okved==code)&ind.year.between(*period)].groupby('year',as_index=False)['stationary_t'].sum()
    st.plotly_chart(fig_style(px.line(trend,x='year',y='stationary_t',markers=True,
                   title=f'Динамика ОКВЭД {code}, тонн',color_discrete_sequence=COLORS,
                   labels={'year':'Год','stationary_t':'тонн'})),use_container_width=True)
    st.caption('ОКВЭД характеризует только стационарные выбросы. Категория «Прочие» сохраняется в суммах.')

with tab4:
    p=d['pollutants']
    pp=p[(p.year==year)&p.region.isin(region_list)].copy()
    pp['emission_kt']=pp.emission_t/1000
    st.subheader(f'Состав стационарных выбросов · {year}')
    st.plotly_chart(fig_style(px.bar(pp,x='region',y='emission_kt',color='substance',barmode='stack',
                    title='Структура по группам веществ, тыс. т',color_discrete_sequence=COLORS,
                    labels={'region':'Регион','emission_kt':'тыс. т','substance':'Вещество'})),
                    use_container_width=True)
    selected_substance=st.selectbox('Загрязняющее вещество',sorted(p.substance.unique()))
    trend=p[(p.substance==selected_substance)&p.region.isin(region_list)&p.year.between(*period)]
    st.plotly_chart(fig_style(px.line(trend,x='year',y='emission_t',color='region',markers=True,
                   title=f'{selected_substance}: динамика, тонн',color_discrete_sequence=COLORS,
                   labels={'year':'Год','emission_t':'тонн','region':'Регион'})),use_container_width=True)
    st.markdown('**Улавливание и утилизация (стационарные источники)**')
    c=d['cleaning'][(d['cleaning'].year==year)&d['cleaning'].region.isin(region_list)].copy()
    view=c[['region','received_t','caught_t','utilized_t','capture_pct','utilization_pct']].copy()
    st.dataframe(view.round(2),hide_index=True,use_container_width=True)
    st.caption('Доля уловленных = уловлено / поступило на очистку. Доля утилизированных = утилизировано / уловлено. Это НЕ доля очистки всех образовавшихся выбросов.')

st.divider()
st.caption('Источник: официальные файлы Росприроднадзора из архива ВКР. Статистика выбросов не равнозначна концентрациям загрязняющих веществ в воздухе.')
with st.expander('Проверка данных и выгрузка'):
    st.write('Сопоставление независимых итогов по ОКТМО и ОКВЭД, тонн:')
    st.dataframe(d['validation'][['year','region','by_oktmo_t','by_okved_t','difference_t']].round(8),
                 hide_index=True,use_container_width=True)
    st.download_button('Скачать выбранные итоговые показатели (CSV)',
        data=yf.to_csv(index=False).encode('utf-8-sig'),
        file_name='vkr_monitoring.csv',mime='text/csv')
