---
layout: default
title: Inicio
---

{% for post in site.posts %}
  <article class="post-card">
    <div class="post-date">{{ post.date | date: "%d · %m · %Y" }}</div>
    <h2><a href="{{ post.url | relative_url }}" style="text-decoration:none; color:inherit;">{{ post.title }}</a></h2>
    <p class="post-excerpt">{{ post.excerpt | strip_html | truncatewords: 35 }}</p>
    {% if post.image %}
      <img src="{{ post.image }}" alt="Ilustración" loading="lazy">
    {% endif %}
    <a href="{{ post.url | relative_url }}" class="read-link">Leer completo →</a>
  </article>
{% else %}
  <div class="post-card">
    <p style="text-align:center; color:#b8a88a; font-style:italic;">Los primeros escritos están brotando... vuelve pronto.</p>
  </div>
{% endfor %}