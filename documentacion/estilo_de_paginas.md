# Sistema de Estilos Centralizado - Drone Acuático

## 📋 Descripción General

El proyecto utiliza un **sistema de estilos centralizado** basado en variables CSS (CSS Custom Properties) que permite mantener una apariencia consistente en todas las páginas y facilita el cambio de tema (oscuro/claro).

Todos los estilos se encuentran en:
- **`paginas/tema.css`** - Estilos centralizados
- **`paginas/tema.js`** - Lógica de cambio de tema

---

## 🎨 Variables CSS Disponibles

### Fondos
```css
--bg-primary      /* Fondo principal con gradiente */
--bg-secondary    /* Fondo secundario para paneles */
--bg-tertiary     /* Fondo terciario para elementos internos */
--header-bg       /* Fondo específico para headers */
--card-bg         /* Fondo para tarjetas */
--input-bg        /* Fondo para inputs */
```

### Textos
```css
--text-primary      /* Texto principal */
--text-secondary    /* Texto secundario */
--text-tertiary     /* Texto terciario (más débil) */
```

### Bordes
```css
--border-color      /* Color de bordes */
--input-border      /* Color de bordes para inputs */
```

### Colores Semánticos
```css
--success-color     /* Verde para éxito (#10b981) */
--danger-color      /* Rojo para peligro (#ef4444) */
--info-color        /* Azul para información (#3b82f6) */
--warning-color     /* Naranja para advertencia (#f59e0b) */
```

### Efectos Visuales
```css
--primary-gradient  /* Gradiente principal (púrpura-azul) */
--shadow            /* Sombra grande (0 8px 32px rgba(0, 0, 0, 0.3)) */
--shadow-sm         /* Sombra pequeña (0 4px 12px rgba(0, 0, 0, 0.15)) */
```

---

## 🌙 Temas Soportados

### Tema Oscuro (Por defecto)
- Colores: Tonos oscuros (#0f1419, #1a2332)
- Gradiente: Azul profundo a gris oscuro
- Bordes: Blancos translúcidos
- Texto: Blanco brillante

**Activación automática** al cargar la página.

### Tema Claro
- Colores: Tonos claros (#f8fafc, #e2e8f0)
- Gradiente: Gris claro a azul claro
- Bordes: Negros translúcidos
- Texto: Gris oscuro (#1e293b)

**Activación** mediante el switch 🌙/☀️ en el header.

---

## 📁 Estructura de Archivos

```
paginas/
├── tema.css              ← Estilos centralizados
├── tema.js               ← Lógica de temas
├── control remoto digital.html
├── configuracion.html
└── [futuras_paginas].html
```

---

## ✅ Cómo Crear una Nueva Página

### 1️⃣ Estructura HTML Básica

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mi Nueva Página - Drone Acuático</title>
    
    <!-- ⚠️ OBLIGATORIO: Importar tema.css -->
    <link rel="stylesheet" href="tema.css">
    
    <style>
        /* Solo estilos específicos de esta página */
        .mi-componente {
            background: var(--card-bg);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            padding: 12px;
            border-radius: 12px;
        }
    </style>
</head>
<body>
    <header>
        <h1>Mi Nueva Página</h1>
        <div style="display: flex; gap: 8px; align-items: center;">
            <!-- ⚠️ RECOMENDADO: Switch de tema -->
            <label class="theme-switch-label" title="Cambiar tema">
                <input type="checkbox" id="toggle-tema" class="switch-checkbox">
                <label for="toggle-tema" class="switch-label">
                    <span class="switch-icon moon">🌙</span>
                    <span class="switch-icon sun">☀️</span>
                </label>
            </label>
            <button class="btn-header" onclick="volverAtras()">⟵ Volver</button>
        </div>
    </header>
    
    <main>
        <!-- Contenido aquí -->
    </main>
    
    <!-- ⚠️ OBLIGATORIO: Script de tema -->
    <script src="tema.js"></script>
    <script>
        // Inicializar tema cuando carga la página
        document.addEventListener('DOMContentLoaded', inicializarTema);
    </script>
</body>
</html>
```

---

## 🎯 Clases CSS Predefinidas

### Botones
```css
.btn              /* Botón azul (info) */
.btn-header       /* Botón pequeño para header */
.btn-volver       /* Botón azul para volver */
.btn-guardar      /* Botón verde */
.btn-cargar       /* Botón naranja */
.btn-rele         /* Botón para relés (gris por defecto) */
.btn-direccion    /* Botón para direcciones */
.btn-menu         /* Botón de menú */
.btn-gps          /* Botón para GPS */

/* Estados */
.btn:hover        /* Efecto hover con sombra y brighten */
.btn:active       /* Efecto de click */
.btn.activo       /* Estado activo (color diferente) */
```

### Indicadores
```css
.estado-conexion           /* Conexión (● Conectado/Desconectado) */
.conectado                 /* Estado conectado (verde) */
.desconectado              /* Estado desconectado (rojo) */

.indicador-ram             /* Indicador de RAM */
.indicador-temp            /* Indicador de temperatura */
.indicador-bat             /* Indicador de batería */
.indicador-red             /* Indicador de red */
.indicador-vel             /* Indicador de velocidad GPS */
.indicador-solar           /* Indicador solar */
.indicador-peso            /* Indicador de peso */

/* Estados de indicadores */
.ram-ok, .temp-ok, .bat-ok           /* Verde */
.ram-warning, .temp-warning           /* Naranja */
.ram-critical, .temp-critical         /* Rojo (con parpadeo) */
```

### Tarjetas y Paneles
```css
.card              /* Tarjeta general */
.panel-controles   /* Panel de control */
.vista-columna     /* Columna en vista */
.seccion-control   /* Sección de control */
.vista-titulo      /* Título de vista con gradiente */
```

### Otros
```css
.dropdown-menu     /* Menú desplegable */
.btn-menu          /* Botón dentro de menú */
.toast             /* Notificación (toast) */
.toast.ok          /* Notificación exitosa */
.toast.warn        /* Notificación de advertencia */
.toast.err         /* Notificación de error */
```

---

## 🔧 Ejemplos de Uso

### Ejemplo 1: Tarjeta Simple
```html
<div class="card">
    <h2>Mi Sección</h2>
    <p style="color: var(--text-secondary);">Descripción con color secundario</p>
    <button class="btn">Acción</button>
</div>
```

### Ejemplo 2: Indicador de Estado
```html
<span class="estado-conexion conectado">● Conectado</span>
<span class="indicador-temp temp-ok">🌡️ 45°C</span>
```

### Ejemplo 3: Formulario
```html
<form>
    <label for="nombre">Nombre:</label>
    <input id="nombre" type="text" placeholder="Ingresa tu nombre">
    
    <label for="opcion">Opción:</label>
    <select id="opcion">
        <option>Opción 1</option>
        <option>Opción 2</option>
    </select>
    
    <button class="btn-guardar" type="submit">Guardar</button>
</form>
```

### Ejemplo 4: Grid Responsivo
```html
<style>
    .mi-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
    }
    
    @media (max-width: 900px) {
        .mi-grid {
            grid-template-columns: 1fr;
        }
    }
</style>

<div class="mi-grid">
    <div class="card">Columna 1</div>
    <div class="card">Columna 2</div>
</div>
```

---

## ⚠️ Buenas Prácticas

### ✅ Hacer
```css
/* Usar variables CSS */
background: var(--card-bg);
color: var(--text-primary);
border: 1px solid var(--border-color);
box-shadow: var(--shadow-sm);
```

### ❌ Evitar
```css
/* NO usar colores hardcodeados */
background: #1e3c72;
color: #ffffff;
border: 1px solid rgba(255, 255, 255, 0.15);
```

### Responsive Design
```css
/* Mobile-first */
.elemento {
    font-size: 12px;
    padding: 8px;
}

@media (min-width: 768px) {
    .elemento {
        font-size: 14px;
        padding: 12px;
    }
}
```

### Animaciones Suaves
```css
/* Las transiciones están en tema.css */
.elemento {
    /* Ya tiene transición automática */
    background: var(--info-color);
}

.elemento:hover {
    filter: brightness(1.1);
    transform: translateY(-2px);
}
```

---

## 🔄 Cambio de Tema

### Automático
El tema se guarda en la base de datos y se carga automáticamente cuando se abre una página:
```javascript
// En tema.js - se ejecuta automáticamente
inicializarTema(); // Carga el tema guardado del servidor
```

### Manual
El usuario puede cambiar el tema con el switch 🌙/☀️:
```javascript
// Se guarda automáticamente en el servidor
// No requiere acción del desarrollador
```

---

## 📱 Responsive Design

El sistema está optimizado para:
- **Escritorio**: Pantallas completas
- **Tablet**: Grids de 2 columnas
- **Móvil**: Grids de 1 columna

Usa `@media (max-width: 900px)` para ajustes tablet.
Usa `@media (max-width: 600px)` para ajustes móvil.

---

## 🎓 Resumen Rápido

| Necesidad | Solución |
|-----------|----------|
| Fondo consistente | Importar `tema.css` |
| Texto legible | Usar `var(--text-primary)` y `var(--text-secondary)` |
| Botones | Usar clases `.btn`, `.btn-guardar`, etc. |
| Tarjetas | Usar clase `.card` |
| Indicadores | Usar clases `.indicador-*` con estados |
| Colores | Usar variables CSS (nunca hardcodear) |
| Tema claro/oscuro | Automático con `tema.js` |
| Sombras | Usar `var(--shadow)` o `var(--shadow-sm)` |
| Bordes | Usar `var(--border-color)` |

---

## 📚 Archivos Relacionados

- [control remoto digital.html](../paginas/control%20remoto%20digital.html) - Ejemplo completo
- [configuracion.html](../paginas/configuracion.html) - Ejemplo de formularios
- [tema.css](../paginas/tema.css) - Definición de todas las variables
- [tema.js](../paginas/tema.js) - Lógica de temas

---

## 📞 Soporte

Para preguntas o cambios en los estilos, referirse a:
- Variables en `tema.css` líneas 1-45
- Clases en `tema.css` líneas 45+
- Lógica en `tema.js`

**Última actualización**: 29 de Diciembre, 2025
**Versión**: 1.0
