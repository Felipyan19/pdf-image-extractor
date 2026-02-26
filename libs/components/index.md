# Librería de Componentes HTML — AMEX Argentina

> **33 componentes** en 19 carpetas | Última actualización: 2026-02-25
>
> Cada componente es un archivo HTML standalone (620px, responsive, MSO-compatible).
> Para detalles estructurales completos ver [`catalog.json`](catalog.json).

---

## Índice por tipo

| # | Tipo | Variantes disponibles |
|---|------|-----------------------|
| 1 | [Preheader](#preheader) | v4.2 · v4.0 |
| 2 | [Brand Panel](#brand-panel) | Consumer · Gold · Platinum |
| 3 | [Hero Banner](#hero-banner) | Overlay v4.2 · Overlay v4.0 |
| 4 | [Hero Full Width](#hero-full-width) | Solo texto · Imagen + barra |
| 5 | [Intro Text](#intro-text) | — |
| 6 | [Sección Compras](#secciones-de-categoría) | — |
| 7 | [Sección Gastronomía](#secciones-de-categoría) | — |
| 8 | [Sección Hoteles](#secciones-de-categoría) | — |
| 9 | [Horizontal Pair](#horizontal-pair) | RTL (imagen der.) · LTR (imagen izq.) · LTR + Logos |
| 10 | [CTA Banner](#cta-banner) | Navy · Blue |
| 11 | [Offer Code Hotel](#offer-code-hotel) | Beneficios · Oferta especial |
| 12 | [Hotel Card](#hotel-card) | LTR (imagen izq.) · RTL (imagen der.) |
| 13 | [Section Divider](#section-divider) | — |
| 14 | [Cross-Sell Icons](#cross-sell-icons) | 2 íconos · 4 íconos |
| 15 | [Contact CTA](#contact-cta) | — |
| 16 | [Footer Tagline](#footer-tagline) | — |
| 17 | [Social Icons](#social-icons) | — |
| 18 | [Footer Nav](#footer-nav) | v4.0 · v4.2 |
| 19 | [Terms](#terms) | v4.0 · v4.2 |
| 20 | [Footer Completo](#footer-completo) | — |

---

## Preheader

| Componente | Archivo | Layout | Descripción Visual | Usar cuando |
|------------|---------|--------|--------------------|-------------|
| Preheader v4.2 | [preheader/preheader-v42.html](preheader/preheader-v42.html) | single-row | Fondo **#E0E0E0** · izq: "PUBLICIDAD" · der: "¿No podés ver el mail?" + link | Emails modernos v4.2 (Platinum, Travel) |
| Preheader v4.0 | [preheader/preheader-v40.html](preheader/preheader-v40.html) | single-row | Fondo **#d9d9d6** · izq: "PUBLICIDAD" · der: "¿No podés ver el mail?" + link | Emails clásicos v4.0 (Gold, Merchant) |

---

## Brand Panel

| Componente | Archivo | Layout | Descripción Visual | Usar cuando |
|------------|---------|--------|--------------------|-------------|
| Brand Panel — Consumer | [brand-panel/brand-panel-consumer.html](brand-panel/brand-panel-consumer.html) | two-row | Fila 1: logo 60px + tagline 150px + datos cuenta + _sin tarjeta_ · Fila 2: "Hola {FULLNAME}" + botón outline "Mi cuenta" | Newsletters de compras/merchant (sin tarjeta específica) |
| Brand Panel — Gold | [brand-panel/brand-panel-gold.html](brand-panel/brand-panel-gold.html) | two-row | Fondo header **#d9d9d6** · logo 80px + tagline + datos cuenta + tarjeta Gold 80px · Fila 2: "Hola {FNAME}" + botón VML "Mi cuenta" | Emails de Gold Credit Card |
| Brand Panel — Platinum | [brand-panel/brand-panel-platinum.html](brand-panel/brand-panel-platinum.html) | two-row | Fondo **#FFFFFF** · logo 60px + tagline 150px + datos cuenta + tarjeta Platinum 80px · Fila 2: "Hola {FULLNAME}" + botón outline "Mi cuenta" | Emails de Platinum Card |

---

## Hero Banner

> Imagen de fondo con texto superpuesto. Variantes por versión de template.

| Componente | Archivo | Layout | Descripción Visual | Usar cuando |
|------------|---------|--------|--------------------|-------------|
| Hero Banner Overlay v4.2 | [hero-banner/hero-banner-overlay-v42.html](hero-banner/hero-banner-overlay-v42.html) | full-width bg image | Imagen BG full-width · texto **centrado** superpuesto: título grande navy + subtítulo fecha uppercase · imagen mobile independiente | Hero principal moderno centrado |
| Hero Banner Overlay v4.0 | [hero-banner/hero-banner-overlay-v40.html](hero-banner/hero-banner-overlay-v40.html) | 3-col bg image | Imagen BG · 3 columnas: spacer 43px \| caja con título navy \| imagen-mobile | Hero con texto alineado a izquierda, versión clásica |

---

## Hero Full Width

> Ocupa todo el ancho del email (620px). Sin imagen de fondo; el contenido es el protagonista.

| Componente | Archivo | Layout | Descripción Visual | Usar cuando |
|------------|---------|--------|--------------------|-------------|
| Hero Full Width — Solo Texto | [hero-full-width/hero-full-width-text.html](hero-full-width/hero-full-width-text.html) | single-col color bg | Fondo **#006fca** · texto blanco grande bold centrado + párrafo blanco con palabras en bold · sin imagen | Anunciar novedades importantes sin imagen (ej: extensión de límite) |
| Hero Full Width — Imagen + Barra | [hero-full-width/hero-full-width-image.html](hero-full-width/hero-full-width-image.html) | stacked: imagen → barra → texto | Fila 1: foto full-width · Fila 2: barra **#5d6165** + título blanco · Fila 3: fondo blanco + descripción navy | Hero de destino/producto con imagen + título + descripción (travel) |

---

## Intro Text

| Componente | Archivo | Layout | Descripción Visual | Usar cuando |
|------------|---------|--------|--------------------|-------------|
| Intro Text | [intro-text/intro-text.html](intro-text/intro-text.html) | single-col white | Fondo blanco · párrafo centrado con texto normal + palabras en **bold azul #006fcf** | Párrafo introductorio que resume los beneficios del período |

---

## Secciones de Categoría

> Bloques que combinan header de sección + contenido en 50/50. Incluyen header azul con ícono + título uppercase.

| Componente | Archivo | Layout | Descripción Visual | Usar cuando |
|------------|---------|--------|--------------------|-------------|
| Sección Compras | [section-compras/section-compras.html](section-compras/section-compras.html) | section-header + 2-col 50/50 | Header **#006FCF**: ícono 51px + "COMPRAS" · Body: divider vertical, izq (título/fecha/imagen/CTA), der (logo/imagen/texto/link) | Sección completa de compras con dos promos (ej: Shopping Days + PedidosYa) |
| Sección Gastronomía | [section-gastronomia/section-gastronomia.html](section-gastronomia/section-gastronomia.html) | section-header + 2-col 50/50 | Header **#006FCF**: ícono 51px + "GASTRONOMÍA" · Body: divider vertical, izq (imagen/texto/link), der (imagen/logos-hoteles/link) | Sección completa de gastronomía con dos promos |
| Sección Hoteles | [section-hoteles/section-hoteles.html](section-hoteles/section-hoteles.html) | section-header + centrado + 2-col | Header **#006FCF**: ícono 51px + "HOTELES" · Body: % descuento grande centrado + 2-col con sub-ofertas | Sección completa de hoteles con beneficio central + dos sub-promos |

---

## Horizontal Pair

> Módulo de promo en dos columnas 50/50: imagen fotográfica + texto de oferta. Variantes por posición de imagen y contenido adicional.

| Componente | Archivo | Layout | Descripción Visual | Usar cuando |
|------------|---------|--------|--------------------|-------------|
| Par Horizontal — Imagen Derecha | [horizontal-pair/horizontal-pair-rtl.html](horizontal-pair/horizontal-pair-rtl.html) | 2-col 50/50 `dir=rtl` | Izq: label-navy + imagen-oferta + texto-azul + texto-navy + **botón azul 130px** + legal · Der: foto 310px | Promo con foto grande a la **derecha** |
| Par Horizontal — Imagen Izquierda | [horizontal-pair/horizontal-pair-ltr.html](horizontal-pair/horizontal-pair-ltr.html) | 2-col 50/50 `dir=ltr` | Izq: foto 310px · Der: label-navy + imagen-oferta + texto-azul + texto-navy + **botón azul 230px** + legal | Promo con foto grande a la **izquierda** |
| Par Horizontal — Imagen Izq. + Logos | [horizontal-pair/horizontal-pair-ltr-logos.html](horizontal-pair/horizontal-pair-ltr-logos.html) | 2-col 50/50 `dir=ltr` | Izq: foto 310px · Der: descripción + imagen-% + **fila de 3 logos de marca** + botón azul 130px + legal | Promo con logos de marcas participantes (supermercados, tiendas) |

---

## CTA Banner

> Banner de una sola fila con texto + link. Fondo de color sólido.

| Componente | Archivo | Layout | Descripción Visual | Usar cuando |
|------------|---------|--------|--------------------|-------------|
| CTA Banner — Navy | [cta-banner/cta-banner-navy.html](cta-banner/cta-banner-navy.html) | single-col | Fondo **#00175A** · texto blanco centrado + link subrayado blanco | Cierre de sección de beneficios, frase corta + "acá" subrayado |
| CTA Banner — Blue | [cta-banner/cta-banner-blue.html](cta-banner/cta-banner-blue.html) | single-col | Fondo **#006FCF** · texto blanco: nombre de tarjeta en bold + link subrayado | CTA que menciona el nombre de la tarjeta (Gold/Platinum), v4.0 |

---

## Offer Code Hotel

> Bloques específicos para campañas de Hotel Collection.

| Componente | Archivo | Layout | Descripción Visual | Usar cuando |
|------------|---------|--------|--------------------|-------------|
| Offer Code — Beneficios Hotel Collection | [offer-code-hotel/offer-code-hotel-benefits.html](offer-code-hotel/offer-code-hotel-benefits.html) | single-col grey | Fondo **#F4F5F6** · logo Hotel Collection 354px + descripción + **grilla 2×2** de 4 beneficios (ícono 39px + texto) + separador | Lista de beneficios del programa: Early Check-in, F&B, Late Check-out, Upgrade |
| Offer Code — Oferta Especial 3ra Noche | [offer-code-hotel/offer-code-hotel-offer.html](offer-code-hotel/offer-code-hotel-offer.html) | single-col white | Fondo blanco · ícono estrella 39px centrado + label "OFERTA ESPECIAL" + headline grande navy + descripción | Encabezado de oferta "3ra noche gratuita", va antes de los hotel-cards |

---

## Hotel Card

> Tarjeta individual de hotel en dos columnas. Se alterna ltr/rtl para crear ritmo visual.

| Componente | Archivo | Layout | Descripción Visual | Usar cuando |
|------------|---------|--------|--------------------|-------------|
| Hotel Card — Imagen Izquierda | [hotel-card/hotel-card-ltr.html](hotel-card/hotel-card-ltr.html) | 2-col 50/50 `dir=ltr` | Fondo **#F4F5F6** · Izq: foto hotel · Der: nombre navy 16px + descripción 15px + validez 10px | Primera tarjeta de hotel (imagen izquierda) |
| Hotel Card — Imagen Derecha | [hotel-card/hotel-card-rtl.html](hotel-card/hotel-card-rtl.html) | 2-col 50/50 `dir=rtl` | Fondo **#F4F5F6** · Izq: nombre navy 16px + descripción 15px + validez 10px · Der: foto hotel | Segunda tarjeta (alterna posición para ritmo visual) |

---

## Section Divider

| Componente | Archivo | Layout | Descripción Visual | Usar cuando |
|------------|---------|--------|--------------------|-------------|
| Divisor de Sección | [section-divider/section-divider.html](section-divider/section-divider.html) | single-row divider | Fondo blanco · **HR gris** + texto uppercase bold 14px centrado + **HR gris** (color #595959) | Separador entre secciones con label (ej: "Platinum Travel Services®") |

---

## Cross-Sell Icons

> Fila de íconos de servicios con links. Variante de 2 íconos incluye divisor integrado.

| Componente | Archivo | Layout | Descripción Visual | Usar cuando |
|------------|---------|--------|--------------------|-------------|
| Cross-Sell — 2 Íconos (con divisor) | [cross-sell-icons/cross-sell-icons-2.html](cross-sell-icons/cross-sell-icons-2.html) | divisor + icon-row 2-col | HR + label "Obtené más de American Express®" + fila de **2 íconos 48px** + texto-link azul · borde inferior #d9d9d6 | Cross-sell con 2 servicios (ej: Adicional, Beneficios). Divisor incluido. |
| Cross-Sell — 4 Íconos (sin divisor) | [cross-sell-icons/cross-sell-icons-4.html](cross-sell-icons/cross-sell-icons-4.html) | icon-row 4-col | Fila de **4 íconos 48px** + label gris debajo · `role="list"` (accesible) · sin divisor propio | Cross-sell de servicios travel: Aéreos, Hoteles, Cruceros, Autos. Requiere section-divider separado. |

---

## Contact CTA

| Componente | Archivo | Layout | Descripción Visual | Usar cuando |
|------------|---------|--------|--------------------|-------------|
| Contact CTA | [contact-cta/contact-cta.html](contact-cta/contact-cta.html) | single-col white | Fondo blanco · texto de instrucción con teléfono + **botón navy #00175A 230px** centrado | Emails de travel Platinum: indicar teléfono de reserva + botón "Conocé más beneficios" |

---

## Footer Tagline

| Componente | Archivo | Layout | Descripción Visual | Usar cuando |
|------------|---------|--------|--------------------|-------------|
| Footer Tagline | [footer-tagline/footer-tagline.html](footer-tagline/footer-tagline.html) | single-col white | Fondo blanco · **imagen tagline centrada 376px** (ej: "No vivas la vida sin ella") | Slogan AMEX antes de social icons |

---

## Social Icons

| Componente | Archivo | Layout | Descripción Visual | Usar cuando |
|------------|---------|--------|--------------------|-------------|
| Social Icons | [social-icons/social-icons.html](social-icons/social-icons.html) | single-row centered | Fondo blanco · **3 íconos 28px** en fila: Instagram \| Facebook \| YouTube · separación 30px | Fila de redes sociales. Va después de footer-tagline. |

---

## Footer Nav

| Componente | Archivo | Layout | Descripción Visual | Usar cuando |
|------------|---------|--------|--------------------|-------------|
| Footer Nav v4.0 | [footer-nav/footer-nav-v40.html](footer-nav/footer-nav-v40.html) | single-row nav | Borde top #DEDEDE · 4 links **#006FCF** · padding `0 30px` · sin roles ARIA | Gold / Merchant (links azules, versión clásica) |
| Footer Nav v4.2 | [footer-nav/footer-nav-v42.html](footer-nav/footer-nav-v42.html) | single-row nav | Borde top #DBDBDB · 4 links **#000000** · padding `0 10px` + display block · con `role="list"` | Platinum / Travel (links negros, versión moderna accesible) |

---

## Terms

| Componente | Archivo | Layout | Descripción Visual | Usar cuando |
|------------|---------|--------|--------------------|-------------|
| Términos v4.0 | [terms/terms-v40.html](terms/terms-v40.html) | single-col grey | Fondo **#D9D9D6** · imagen CFT 367px + bloque texto TyC uppercase 13px justificado + {EMAIL} | Gold / Merchant (incluye imagen CFT, fondo beige) |
| Términos v4.2 | [terms/terms-v42.html](terms/terms-v42.html) | single-col grey | Fondo **#E0E0E0** · solo texto TyC uppercase 13px justificado + {EMAIL} (sin imagen CFT) | Platinum / Travel (sin imagen CFT, fondo gris claro) |

---

## Footer Completo

| Componente | Archivo | Layout | Descripción Visual | Usar cuando |
|------------|---------|--------|--------------------|-------------|
| Footer Combinado | [footer/footer-combined.html](footer/footer-combined.html) | stacked footer | **4 secciones apiladas**: tagline + social icons + footer-nav v4.2 + terms v4.2 | Insertar el footer entero como un solo bloque. Alternativa: usar los 4 componentes individuales. |

---

## Guía de ensamble — secuencia típica

### Email de Compras/Merchant (v4.0)
```
preheader-v40 → brand-panel-consumer → hero-banner-overlay-v40
→ intro-text → section-compras → section-gastronomia
→ cta-banner-navy → cross-sell-icons-2
→ footer-tagline → social-icons → footer-nav-v40 → terms-v40
```

### Email de Tarjeta Específica (Gold)
```
preheader-v40 → brand-panel-gold → hero-banner-overlay-v42
→ horizontal-pair-rtl → horizontal-pair-ltr → cta-banner-blue
→ footer-tagline → social-icons → footer-nav-v40 → terms-v40
```

### Email de Travel (Platinum)
```
preheader-v42 → brand-panel-platinum → hero-full-width-image
→ section-divider → offer-code-hotel-benefits → offer-code-hotel-offer
→ hotel-card-ltr → hotel-card-rtl → contact-cta
→ cross-sell-icons-4 → footer-combined
```
