---
title: "카카오톡 선물하기 CRM 분석 — 참고 자료 및 논문"
date: 2026-04-04
tags: [references, papers, industry-standards]
---

# 참고 자료 및 논문 목록

## Layer 1: EDA & 시즌 분석

### 학술 논문 & 공식 문서
- **Cleveland, R. B., Cleveland, W. S., McRae, J. E., & Terpenning, I. (1990)**  
  "STL: A Seasonal-Trend Decomposition. Official method."  
  Journal of Official Statistics, 6(1), 3-73.  
  [Link](https://www.scb.se/en/Services/Statistical-methods-and-IT-tools/Statistical-methods/Seasonal-adjustment/)

- **statsmodels Official Documentation**  
  "Seasonal-Trend decomposition using LOESS (STL)"  
  [Link](https://www.statsmodels.org/generated/statsmodels.tsa.seasonal.STL.html)

### 실무 자료
- [GeeksforGeeks: Seasonal Decomposition of Time Series by Loess](https://www.geeksforgeeks.com/data-analysis/seasonal-decomposition-of-time-series-by-loess-stl/)
- [Towards Data Science: STL Decomposition — Understanding Initial Trend](https://towardsdatascience.com/time-series-forecasting-made-simple-part-3-1-stl-decomposition-understanding-initial-trend-and-seasonality-prior-to-loess-smoothing/)

---

## Layer 2: RFM 세그멘테이션

### 학술 논문
- **Hughes, A. M. (1994)**  
  "Strategic Database Marketing: The Methodology to Improve Marketing ROI"  
  Chicago: Probus Publishing.  
  [Original RFM Definition - Industry Standard]

- **Óskarsson, H. (2022)**  
  "A multi layer recency frequency monetary method for customer priority segmentation in online transaction"  
  Journal of Big Data, 9(57).  
  [Link](https://www.tandfonline.com/doi/full/10.1080/23311916.2022.2162679)

- **IEEE Conference (2024)**  
  "Customer Segmentation through RFM Analysis and K-means Clustering: Leveraging Data-Driven Insights for Effective Marketing Strategy"  
  [Link](https://ieeexplore.ieee.org/document/10630052/)

### 실무 자료
- [Rittman Analytics: RFM Analysis and Customer Segmentation using dbt + BigQuery](https://rittmananalytics.com/blog/2021/6/20/rfm-analysis-and-customer-segmentation-using-looker-dbt-and-google-bigquery)

- [Medium: Comparative Study of K-Means Clustering vs Rule-Based Segmentation for RFM](https://medium.com/@zargi.teddy7/a-comparative-study-of-k-means-clustering-and-rule-based-segmentation-for-rfm-analysis-on-the-uci-5ca3db89fc0b)

- [RetailReco: RFM Analysis for Customer Segmentation](https://www.retailreco.com/blog/rfm-analysis-for-customer-segmentation-in-ecommerce)

---

## Layer 3: LTV & 코호트 분석

### 학술 논문
- **Fader, P. S., Hardie, B. G., & Lee, K. L. (2005)**  
  "Counting Your Customers" the Easy Way: An Alternative to the Pareto/NBD Model"  
  Marketing Science, 24(2), 275-284.  
  [BG/NBD Original Paper - Non-contractual CLV]

- **Schmittlein, D. C., Morrison, D. G., & Colombo, R. C. (1987)**  
  "Counting Your Customers: Who Are They and What Will They Do?"  
  Management Science, 33(1), 1-24.  
  [Pareto/NBD Original Paper]

### 실무 자료 & 라이브러리
- **lifetimes Python Library**  
  [Official Documentation](https://lifetimes.readthedocs.io/en/latest/Quickstart.html)
  
  ```python
  from lifetimes import BetaGeoFitter, GammaGammaFitter
  ```

- [PyMC-Marketing: Pareto/NBD Model](https://www.pymc-marketing.io/en/latest/notebooks/clv/pareto_nbd.html)

- [Medium: Projecting CLV using BG/NBD and Gamma-Gamma](https://medium.com/@yassirafif/projecting-customer-lifetime-value-using-the-bg-nbd-and-the-gamma-gamma-models-9a937c60fe7f)

- [Baremetrics: How to Use Cohort Analysis to Reduce Churn](https://baremetrics.com/blog/cohort-analysis)

- [Peel Insights: Cohort Analysis 101](https://www.peelinsights.com/post/cohort-analysis-101-an-introduction)

---

## Layer 4: Viral Loop & Network Effect

### 학술 논문
- **Kermack, W. O., & McKendrick, A. G. (1927)**  
  "A contribution to the mathematical theory of epidemics"  
  Proceedings of the Royal Society A, 115(772), 700-721.  
  [Foundational SIR Model - Viral Spread Theory]

- **Newman, M. E. J. (2003)**  
  "The structure and function of complex networks"  
  SIAM Review, 45(2), 167-256.  
  [Network Analysis Foundation]

- **Transition of social organisations driven by gift relationships (2023)**  
  Nature Humanities and Social Sciences Communications  
  [Link](https://www.nature.com/articles/s41599-023-01688-w)

- **Reciprocity as the Foundational Substrate of Society**  
  arXiv:2505.08319v2  
  [Link](https://arxiv.org/html/2505.08319v2)

### 실무 자료
- **FirstRound Review: K-factor: The Metric Behind Virality**  
  [Link](https://review.firstround.com/glossary/k-factor-virality/)

- **MetricHQ: Viral Coefficient**  
  [Link](https://www.metrichq.org/marketing/viral-coefficient/)

- **Dropbox Referral Program Case Study**  
  "How Dropbox Marketing Achieved 3900% Growth with Referrals"  
  [Link](https://viral-loops.com/blog/dropbox-grew-3900-simple-referral-program/)

- **OpenView: The Network Effect and Viral Coefficient**  
  [Link](https://openviewpartners.com/blog/the-network-effect-and-the-importance-of-the-viral-coefficient-for-saas-companies/)

- **Kurve: How to Measure Referral Success**  
  [Link](https://kurve.co.uk/blog/app-referral-marketing-k-factor-viral-retention)

---

## Layer 5: CRM 캠페인 & Incrementality

### 학술 논문
- **Gutierrez, P., & Gérardy, J. Y. (2017)**  
  "Causal Inference and Uplift Modeling: A review of the literature"  
  Journal of Machine Learning Research (JMLR), JMLR Workshop and Conference Proceedings, Vol. 67  
  [Link](https://proceedings.mlr.press/v67/gutierrez17a/gutierrez17a.pdf)

- **Enhancing Uplift Modeling in Multi-Treatment Marketing Campaigns (2024)**  
  arXiv:2408.13628  
  [Link](https://arxiv.org/html/2408.13628)

- **Uplift Modeling: from Causal Inference to Personalization**  
  arXiv:2308.09066  
  [Link](https://arxiv.org/abs/2308.09066)

### 실무 자료
- **Measured: Incrementality-based Attribution**  
  [Why Incrementality is Better Than MTA/MMM](https://www.measured.com/blog/why-incrementality-based-attribution-is-better-for-optimizing-roas-than-mmm-or-mta-a-real-world-example/)

- **Remerge: A Quick Guide to Interpreting Incremental ROAS**  
  [Link](https://www.remerge.io/findings/blog-post/a-quick-guide-to-interpreting-incremental-roas)

- **Cometly: Incrementality Testing for Marketing**  
  [Complete Guide](https://www.cometly.com/post/incrementality-testing-for-marketing)

- **Medium: Uplift Modeling — Predict the Causal Effect**  
  [Link](https://medium.com/data-reply-it-datatech/uplift-modeling-predict-the-causal-effect-of-marketing-communications-24385fb04f2e)

- **Uber causalml: GitHub Repository**  
  [Uplift modeling library](https://github.com/uber/causalml)

---

## 일반 참고 자료

### CRM & 마케팅 표준
- **Braze Currents: Message Engagement Events**  
  [Link](https://www.braze.com/docs/user_guide/data/distribution/braze_currents/event_glossary/message_engagement_events)

- **Klaviyo Developer: Data Model**  
  [Link](https://developers.klaviyo.com/en/docs/introduction_to_klaviyos_data_model)

- **dbt Best Practices: How We Structure Our Projects**  
  [Link](https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview)

### 데이터 분석 도구
- **pandas Documentation**  
  [Link](https://pandas.pydata.org/docs/)

- **scipy.stats: Statistical Tests**  
  [Link](https://docs.scipy.org/doc/scipy/reference/stats.html)

- **matplotlib + seaborn: Visualization**  
  [Link](https://matplotlib.org/), [Link](https://seaborn.pydata.org/)

- **PySpark SQL: Big Data Processing**  
  [Link](https://spark.apache.org/docs/latest/sql-programming-guide.html)

---

## 업계 사례 연구

### e-Commerce
- **fivetran/dbt_shopify**  
  실전 이커머스 스키마 (GitHub)  
  [Link](https://github.com/fivetran/dbt_shopify)

- **GrabGifts Product Breakdown**  
  선물 서비스 분석 사례  
  [Link](https://anirudhkannanvp.medium.com/decoding-grabgifts-product-breakdown-of-grab-a-technical-product-managers-comprehensive-d90d1cd1aa4f)

### 카카오 기술 블로그
- **카카오 기술블로그: 데이터 파이프라인**  
  [Link](https://tech.kakao.com/2022/04/19/2022-kakao-tech-internship-data/)

---

## 추천 학습 순서

### 입문 (Sophie Level)
1. Hughes (1994) — RFM 기초 개념
2. STL Decomposition — 시계열 분해
3. Cohort Analysis — 간단한 LTV 계산
4. Dropbox Case Study — 바이럴 루프 실제 사례

### 중급
5. Fader et al. (2005) — BG/NBD 모델
6. Uplift Modeling — Causal Inference 소개
7. Braze/Klaviyo 표준 — 실무 데이터 모델링

### 고급
8. Newman (2003) — Network 분석
9. Gutierrez & Gérardy (2017) — Causal Inference 심화
10. PyMC-Marketing — 베이지안 CLV 모델

---

## 키워드별 인덱스

- **Seasonality**: STL Decomposition, Time Series
- **Segmentation**: RFM, K-Means, Rule-Based
- **Lifetime Value**: BG/NBD, Pareto/NBD, Cohort Analysis
- **Viral Growth**: K-factor, Network Effect, Referral
- **CRM**: Incrementality, Uplift Modeling, Attribution
- **Implementation**: pandas, PySpark, dbt, Python

---

**최종 업데이트**: 2026-04-04  
**검토 상태**: Researcher 완료, Sophie 검토 대기
