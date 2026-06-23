---
permalink: /
title: "Fan Cheng"
author_profile: true
hide_title: true
redirect_from:
  - /about/
  - /about.html
---

## Current Position

Ph.D. Candidate in Optics, School of Electrical Engineering, Tel Aviv University, Israel.

{% assign research_interests = site.author.research_interests %}
{% if research_interests and research_interests.items %}
<section class="research-interests" aria-labelledby="research-interests-title">
  <div class="research-interests__body">
    <h2 id="research-interests-title" class="research-interests__title">{{ research_interests.title }}</h2>
    <ul class="research-interests__list">
      {% for interest in research_interests.items %}
      <li>{{ interest }}</li>
      {% endfor %}
    </ul>
  </div>
  <div class="research-signatures" aria-label="Representative research images">
    <figure class="research-signatures__item">
      <a class="research-signatures__link" href="{{ '/publications/#publication-publication-2025-09-22-resonantly-enhanced-evaporation-sensing-in-liquid-droplet-whispering-gallery-cavities' | relative_url }}" data-destination="Applied Physics Letters (2025)" title="Open Applied Physics Letters (2025)" aria-label="Open Applied Physics Letters (2025)">
        <img src="{{ '/files/papers/figures/about-2025-apl-droplet-evaporation-panel-e.png' | relative_url }}" alt="Fig. 1(e) superposition of the whispering-gallery mode and liquid droplet used for evaporation sensing" width="264" height="300" loading="lazy" decoding="async">
      </a>
    </figure>
    <figure class="research-signatures__item">
      <a class="research-signatures__link" href="{{ '/publications/#publication-publication-2024-03-01-cavity-continuum' | relative_url }}" data-destination="Photonics Research (2024)" title="Open Photonics Research (2024)" aria-label="Open Photonics Research (2024)">
        <img src="{{ '/files/papers/figures/about-2024-photonics-research-cavity-continuum-panel-d.png' | relative_url }}" alt="Fig. 2(d) fluorescence image of coupled oil droplets in a cavity-continuum experiment" width="244" height="258" loading="lazy" decoding="async">
      </a>
    </figure>
  </div>
</section>
{% endif %}

{% assign pub_apl_2025 = site.publications | where: "doi", "10.1063/5.0279509" | first %}
{% assign pub_optica_2025 = site.publications | where: "doi", "10.1364/OPTICA.560597" | first %}
{% assign pub_oe_2025 = site.publications | where: "doi", "10.1364/OE.561188" | first %}
{% assign pub_pr_2024 = site.publications | where: "doi", "10.1364/PRJ.505164" | first %}
{% assign pub_aip_2024 = site.publications | where: "doi", "10.1063/5.0197109" | first %}
{% assign pub_nc_2023 = site.publications | where: "doi", "10.1038/s41467-023-40205-0" | first %}
{% assign pub_oe_2018 = site.publications | where: "doi", "10.1364/oe.26.031500" | first %}

## News

<ul class="site-news">
  <li class="site-news__item site-news__item--key site-news__item--award"><span class="site-news__award-layout"><span class="site-news__award-copy">2026-03: <strong>Award:</strong> <a href="/cv/#award-student-excellence-gertner">Student Excellence Award from <span class="text-nowrap">The Marian Gertner Institute</span> for <span class="text-nowrap">Medical Nanosystems</span></a>.</span> {% include gertner-award-brand.html href="/cv/#award-student-excellence-gertner" title="Open Student Excellence Award details in CV" variant="two-line" %}</span></li>
  <li class="site-news__item site-news__item--key">2025-09: <strong>First-author paper:</strong> Published in {% include news-publication-meta.html publication=pub_apl_2025 href="/publications/#publication-publication-2025-09-22-resonantly-enhanced-evaporation-sensing-in-liquid-droplet-whispering-gallery-cavities" %}.</li>
  <li class="site-news__item">2025-09: <strong>Co-author paper:</strong> Published in {% include news-publication-meta.html publication=pub_optica_2025 href="/publications/#publication-publication-2025-09-20-photonic-origami-of-silica-on-a-silicon-chip-with-microresonators-and-concave-mirrors" %}; featured in {% include news-brand-logo.html name="Optics & Photonics News" logo="/files/papers/figures/logos/optics-photonics-news-logo.svg" href="/publications/#publication-publication-2025-09-20-photonic-origami-of-silica-on-a-silicon-chip-with-microresonators-and-concave-mirrors" %}.</li>
  <li class="site-news__item">2025-07: <strong>Co-author paper:</strong> Published in {% include news-publication-meta.html publication=pub_oe_2025 href="/publications/#publication-publication-2025-07-28-observation-of-spectrally-continuous-resonance-enhancement-by-mode-coalescence" %}.</li>
  <li class="site-news__item site-news__item--key">2024-03: <strong>First-author paper:</strong> Published in {% include news-publication-meta.html publication=pub_pr_2024 href="/publications/#publication-publication-2024-03-01-cavity-continuum" %}.</li>
  <li class="site-news__item">2024-03: <strong>Co-author paper:</strong> Published in {% include news-publication-meta.html publication=pub_aip_2024 href="/publications/#publication-publication-2024-03-01-radiation-pressure-induced-oscillations-of-an-optically-levitating-mirror" %}.</li>
  <li class="site-news__item">2023-07: <strong>Co-author paper:</strong> Published in {% include news-publication-meta.html publication=pub_nc_2023 href="/publications/#publication-publication-2023-07-27-absorption-induced-transmission-in-plasma-microphotonics" %}; featured in {% include news-brand-logo.html name="Optics & Photonics News" logo="/files/papers/figures/logos/optics-photonics-news-logo.svg" href="/publications/#publication-publication-2023-07-27-absorption-induced-transmission-in-plasma-microphotonics" %}.</li>
</ul>

<details class="site-news__archive">
  <summary>Earlier News</summary>
  <ul class="site-news site-news--older">
    <li class="site-news__item">2018-11: <strong>Co-author paper:</strong> Published in {% include news-publication-meta.html publication=pub_oe_2018 href="/publications/#publication-publication-2018-11-26-nondestructive-measurement-of-nanofiber-diameters-using-microfiber-tip" %}.</li>
  </ul>
</details>

{% assign collaborators = site.author.collaborators %}
{% if collaborators and collaborators.groups %}
<section class="collaborators" aria-labelledby="collaborators-title">
  <h2 id="collaborators-title" class="collaborators__title">{{ collaborators.title }}</h2>
  <div class="collaborators__grid">
    {% for group in collaborators.groups %}
    <details class="collaborators__group">
      <summary class="collaborators__summary" aria-label="Show {{ group.institution }} collaborators" title="{{ group.institution }} collaborators">
        <span class="collaborators__logo-slot">
          <img class="collaborators__logo" src="{{ group.logo | relative_url }}" alt="{{ group.institution }} logo" width="{{ group.logo_width }}" height="{{ group.logo_height }}" loading="eager" fetchpriority="high">
        </span>
      </summary>
      <ul class="collaborators__people">
        {% for person in group.people %}
        {% assign person_url = person.url | default: person.google_scholar %}
        {% assign person_profile_label = person.profile_label | default: "Google Scholar" %}
        <li><a href="{{ person_url }}" target="_blank" rel="noopener" title="Open {{ person.name }} on {{ person_profile_label | escape }}">{{ person.name }}</a></li>
        {% endfor %}
      </ul>
    </details>
    {% endfor %}
  </div>
</section>
{% endif %}

<p class="site-last-updated">Last updated: {{ site.time | date: "%b %d, %Y" }}</p>
<p class="site-privacy-notice">This site uses Google Analytics to collect anonymized usage statistics. No personally identifiable information is collected.</p>
