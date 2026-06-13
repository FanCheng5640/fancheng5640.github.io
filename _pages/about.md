---
permalink: /
title: "Fan Cheng"
author_profile: true
redirect_from:
  - /about/
  - /about.html
---

## Current Position

Ph.D. Candidate, School of Electrical Engineering, Tel Aviv University, Israel.

{% assign research_interests = site.author.research_interests %}
{% if research_interests and research_interests.items %}
## {{ research_interests.title }}

{% for interest in research_interests.items %}
- {{ interest }}
{% endfor %}
{% endif %}

## News

<ul class="site-news">
  <li class="site-news__item site-news__item--key">3 Mar 2026: <strong>Award:</strong> Student Excellence Award from The Marian Gertner Institute for Medical Nanosystems.</li>
  <li class="site-news__item">1 Dec 2025: <strong>Co-author paper featured:</strong> The <em>Optica</em> paper was featured in <em>Optics &amp; Photonics News</em>.</li>
  <li class="site-news__item site-news__item--key">22 Sep 2025: <strong>First-author paper:</strong> Published in <em>Applied Physics Letters</em>.</li>
  <li class="site-news__item">20 Sep 2025: <strong>Co-author paper:</strong> Published in <em>Optica</em>.</li>
  <li class="site-news__item">28 Jul 2025: <strong>Co-author paper:</strong> Published in <em>Optics Express</em>.</li>
  <li class="site-news__item site-news__item--key">1 Mar 2024: <strong>First-author paper:</strong> Published in <em>Photonics Research</em>.</li>
  <li class="site-news__item">1 Mar 2024: <strong>Co-author paper:</strong> Published in <em>AIP Advances</em>.</li>
  <li class="site-news__item">1 Dec 2023: <strong>Co-author paper featured:</strong> The <em>Nature Communications</em> paper was featured in <em>Optics &amp; Photonics News</em>.</li>
  <li class="site-news__item">27 Jul 2023: <strong>Co-author paper:</strong> Published in <em>Nature Communications</em>.</li>
  <li class="site-news__item">26 Nov 2018: <strong>Co-author paper:</strong> Published in <em>Optics Express</em>.</li>
</ul>
