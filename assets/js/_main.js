/* ==========================================================================
   Various functions that we want to use within the template
   ========================================================================== */

// Determine the expected state of the theme toggle, which can be "dark", "light", or
// "system". Default is "system".
let determineThemeSetting = () => {
  let themeSetting = localStorage.getItem("theme");
  return (themeSetting != "dark" && themeSetting != "light" && themeSetting != "system") ? "system" : themeSetting;
};

// Determine the computed theme, which can be "dark" or "light". If the theme setting is
// "system", the computed theme is determined based on the user's system preference.
let determineComputedTheme = () => {
  let themeSetting = determineThemeSetting();
  if (themeSetting != "system") {
    return themeSetting;
  }
  return (userPref && userPref("(prefers-color-scheme: dark)").matches) ? "dark" : "light";
};

// detect OS/browser preference
const browserPref = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';

// Set the theme on page load or when explicitly called
let setTheme = (theme) => {
  const use_theme =
    theme ||
    localStorage.getItem("theme") ||
    $("html").attr("data-theme") ||
    browserPref;

  if (use_theme === "dark") {
    $("html").attr("data-theme", "dark");
    $("#theme-icon").removeClass("fa-sun").addClass("fa-moon");
  } else if (use_theme === "light") {
    $("html").removeAttr("data-theme");
    $("#theme-icon").removeClass("fa-moon").addClass("fa-sun");
  }
};

// Toggle the theme manually
var toggleTheme = () => {
  const current_theme = $("html").attr("data-theme");
  const new_theme = current_theme === "dark" ? "light" : "dark";
  localStorage.setItem("theme", new_theme);
  setTheme(new_theme);
};

let initPublicationFigureDialogs = () => {
  const playPublicationVideo = (video) => {
    video.muted = true;
    video.loop = true;
    const play = () => {
      const playPromise = video.play();
      if (playPromise && typeof playPromise.catch === "function") {
        playPromise.catch(() => {});
      }
    };
    const retryIfPaused = () => {
      if (video.paused) {
        play();
      }
    };
    play();
    video.addEventListener("canplay", retryIfPaused, { once: true });
    window.setTimeout(retryIfPaused, 180);
    window.setTimeout(retryIfPaused, 700);
  };

  const prepareDialogMedia = (dialog) => {
    dialog.querySelectorAll("[data-publication-video-frame]").forEach((frame) => {
      const src = frame.getAttribute("data-src");
      if (src && frame.getAttribute("src") !== src) {
        frame.setAttribute("src", src);
      }
    });
    dialog.querySelectorAll("[data-publication-video]").forEach((video) => {
      playPublicationVideo(video);
    });
  };

  const stopDialogMedia = (dialog) => {
    dialog.querySelectorAll("[data-publication-video]").forEach((video) => {
      video.pause();
    });
    dialog.querySelectorAll("[data-publication-video-frame]").forEach((frame) => {
      frame.removeAttribute("src");
    });
  };

  const triggers = document.querySelectorAll("[data-publication-figure-open]");
  triggers.forEach((trigger) => {
    const dialogId = trigger.getAttribute("aria-controls");
    const dialog = dialogId ? document.getElementById(dialogId) : null;
    if (!dialog || typeof dialog.showModal !== "function") {
      return;
    }
    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      if (!dialog.open) {
        dialog.showModal();
        prepareDialogMedia(dialog);
      }
    });
  });

  const dialogs = document.querySelectorAll("[data-publication-figure-dialog]");
  dialogs.forEach((dialog) => {
    const closeButton = dialog.querySelector("[data-publication-figure-close]");
    if (closeButton) {
      closeButton.addEventListener("click", () => dialog.close());
    }
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) {
        dialog.close();
      }
    });
    dialog.addEventListener("close", () => {
      stopDialogMedia(dialog);
    });
  });
};

let copyTextToClipboard = (text) => {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text);
  }
  return new Promise((resolve, reject) => {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    try {
      const ok = document.execCommand("copy");
      document.body.removeChild(textarea);
      ok ? resolve() : reject(new Error("copy command failed"));
    } catch (err) {
      document.body.removeChild(textarea);
      reject(err);
    }
  });
};

let initCopyButtons = () => {
  const buttons = document.querySelectorAll("[data-copy-text]");
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const text = button.getAttribute("data-copy-text") || "";
      const statusId = button.getAttribute("data-copy-status-id");
      const status = statusId ? document.getElementById(statusId) : null;
      copyTextToClipboard(text).then(() => {
        if (status) {
          status.textContent = "Copied";
          window.setTimeout(() => {
            status.textContent = "";
          }, 1800);
        }
      }).catch(() => {
        if (status) {
          status.textContent = "Copy failed";
        }
      });
    });
  });
};

let initPublicationListLayout = () => {
  const items = document.querySelectorAll(".publication__item");
  if (items.length === 0) {
    return;
  }

  const getLineCount = (element) => {
    const styles = window.getComputedStyle(element);
    const fontSize = parseFloat(styles.fontSize) || 16;
    let lineHeight = parseFloat(styles.lineHeight);
    if (!lineHeight) {
      lineHeight = fontSize * 1.2;
    }

    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        return node.textContent.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      },
    });
    const centers = [];
    while (walker.nextNode()) {
      const range = document.createRange();
      range.selectNodeContents(walker.currentNode);
      Array.from(range.getClientRects()).forEach((rect) => {
        if (rect.width > 1 && rect.height > 1) {
          centers.push(rect.top + (rect.height / 2));
        }
      });
    }

    if (centers.length === 0) {
      return element.getBoundingClientRect().height / lineHeight;
    }

    const lineThreshold = Math.max(4, lineHeight * 0.65);
    return centers
      .sort((a, b) => a - b)
      .reduce((count, center) => {
        if (count === 0 || Math.abs(center - centers[count - 1]) > lineThreshold) {
          centers[count] = center;
          return count + 1;
        }
        return count;
      }, 0);
  };

  const layoutItem = (item) => {
    const authors = item.querySelector(".publication__authors");
    const cluster = item.querySelector(".publication__visual-cluster");
    const logoRow = item.querySelector(".publication__journal-logo-row");
    const meta = item.querySelector(".publication__meta");
    const image = cluster ? cluster.querySelector(".publication__figure-trigger img") : null;
    const figure = cluster ? cluster.querySelector(".publication__figure--list") : null;
    const citationBadge = meta ? meta.querySelector(".publication__badge--citations") : null;
    const videoCount = item.querySelectorAll(".publication__video-card").length;

    if (!authors || !cluster || !image) {
      return;
    }

    const revealCluster = () => {
      cluster.style.removeProperty("visibility");
      item.classList.add("publication__item--layout-ready");
    };

    item.classList.remove("publication__item--layout-ready");
    cluster.style.visibility = "hidden";
    if (!image.complete || image.naturalWidth === 0) {
      image.addEventListener("load", scheduleLayout, { once: true });
      image.addEventListener("error", revealCluster, { once: true });
      return;
    }
    image.style.removeProperty("max-height");
    cluster.style.removeProperty("width");
    cluster.style.removeProperty("max-width");
    item.classList.remove("publication__item--figure-after-authors");
    item.classList.remove("publication__item--figure-after-meta");

    cluster.style.display = "none";
    const baselineCounts = {
      authors: getLineCount(authors),
      meta: meta ? getLineCount(meta) : 1,
      citation: citationBadge ? getLineCount(citationBadge) : 1,
    };
    cluster.style.removeProperty("display");

    const isSingleColumn = window.matchMedia("(max-width: 520px)").matches;
    const isLandscapeFigure = figure && (
      figure.classList.contains("publication__figure--orientation-landscape") ||
      figure.classList.contains("publication__figure--orientation-wide")
    );
    const isPortraitFigure = figure && figure.classList.contains("publication__figure--orientation-portrait");
    const canUseWideLandscape = () => (
      (item.classList.contains("publication__item--text-figure-only") || videoCount <= 1) &&
      isLandscapeFigure
    );

    const getCurrentCounts = () => ({
      authors: getLineCount(authors),
      meta: meta ? getLineCount(meta) : 1,
      citation: citationBadge ? getLineCount(citationBadge) : 1,
    });
    const exceedsBaseline = (counts) => (
      counts.authors > baselineCounts.authors ||
      counts.meta > baselineCounts.meta ||
      counts.citation > baselineCounts.citation
    );
    const resetCandidateStyles = () => {
      image.style.removeProperty("max-height");
      cluster.style.removeProperty("width");
      cluster.style.removeProperty("max-width");
      item.classList.remove("publication__item--figure-after-authors");
      item.classList.remove("publication__item--figure-after-meta");
    };
    const setPlacement = (placement) => {
      item.classList.remove("publication__item--figure-after-authors");
      item.classList.remove("publication__item--figure-after-meta");
      if (placement === "after-meta" && meta) {
        item.classList.add("publication__item--figure-after-authors");
        item.classList.add("publication__item--figure-after-meta");
        meta.after(cluster);
      } else if (placement === "after-authors") {
        item.classList.add("publication__item--figure-after-authors");
        authors.after(cluster);
      } else {
        authors.before(cluster);
      }
    };
    const applyCandidateWidth = (candidate) => {
      if (candidate.width) {
        cluster.style.width = candidate.width;
      }
      if (candidate.maxWidth) {
        cluster.style.maxWidth = candidate.maxWidth;
      }
    };
    const getSafeBeforeAuthorsWidth = () => {
      resetCandidateStyles();
      setPlacement("before-authors");
      if (!exceedsBaseline(getCurrentCounts())) {
        return null;
      }

      const initialClusterWidth = Math.floor(cluster.getBoundingClientRect().width);
      let low = 1;
      let high = initialClusterWidth;
      let bestWidth = 0;

      while (low <= high) {
        const testWidth = Math.floor((low + high) / 2);
        cluster.style.width = `${testWidth}px`;
        cluster.style.maxWidth = `${testWidth}px`;
        const currentCounts = getCurrentCounts();

        if (exceedsBaseline(currentCounts)) {
          high = testWidth - 1;
        } else {
          bestWidth = testWidth;
          low = testWidth + 1;
        }
      }

      resetCandidateStyles();
      return bestWidth > 0 ? bestWidth : 0;
    };
    const canGrowToLogoForPlacement = (placement) => {
      const isAfterAuthorsOrMeta = placement === "after-authors" || placement === "after-meta";
      const canGrowLandscapeToLogo = isAfterAuthorsOrMeta && canUseWideLandscape();
      const canGrowPortraitToLogo =
        placement === "before-authors" &&
        (videoCount > 1 || item.classList.contains("publication__item--text-figure-only")) &&
        isPortraitFigure;
      return canGrowLandscapeToLogo || canGrowPortraitToLogo;
    };
    const getLogoLimitedImageSize = (placement) => {
      let imageBox = image.getBoundingClientRect();
      if (!logoRow) {
        return {
          width: imageBox.width,
          height: imageBox.height,
        };
      }

      const logoBox = logoRow.getBoundingClientRect();
      const availableHeight = Math.floor(logoBox.bottom - imageBox.top - 1);
      if (canGrowToLogoForPlacement(placement) && availableHeight > imageBox.height + 1) {
        image.style.maxHeight = `${availableHeight}px`;
        imageBox = image.getBoundingClientRect();
      }

      const finalAvailableHeight = Math.floor(logoBox.bottom - imageBox.top - 1);
      if (finalAvailableHeight <= 0 || imageBox.height <= 0) {
        return {
          width: 0,
          height: 0,
        };
      }
      if (imageBox.height <= finalAvailableHeight) {
        return {
          width: imageBox.width,
          height: imageBox.height,
        };
      }
      const scale = finalAvailableHeight / imageBox.height;
      return {
        width: imageBox.width * scale,
        height: finalAvailableHeight,
      };
    };
    const measureCandidate = (placement, options = {}) => {
      resetCandidateStyles();
      setPlacement(placement);
      if (options.fixedWidth) {
        cluster.style.width = `${options.fixedWidth}px`;
        cluster.style.maxWidth = `${options.fixedWidth}px`;
      } else if ((placement === "after-authors" || placement === "after-meta") && canUseWideLandscape()) {
        cluster.style.width = "min(100%, 34rem)";
        cluster.style.maxWidth = "34rem";
      }

      if (exceedsBaseline(getCurrentCounts())) {
        if (!((placement === "after-authors" || placement === "after-meta") && canUseWideLandscape())) {
          return null;
        }

        let low = 1;
        let high = Math.floor(cluster.getBoundingClientRect().width);
        let bestWidth = 0;
        while (low <= high) {
          const testWidth = Math.floor((low + high) / 2);
          cluster.style.width = `${testWidth}px`;
          cluster.style.maxWidth = `${testWidth}px`;

          if (exceedsBaseline(getCurrentCounts())) {
            high = testWidth - 1;
          } else {
            bestWidth = testWidth;
            low = testWidth + 1;
          }
        }

        if (bestWidth <= 0) {
          return null;
        }
        cluster.style.width = `${bestWidth}px`;
        cluster.style.maxWidth = `${bestWidth}px`;
      }

      const size = getLogoLimitedImageSize(placement);
      if (size.width <= 0 || size.height <= 0) {
        return null;
      }

      return {
        placement,
        width: cluster.style.width,
        maxWidth: cluster.style.maxWidth,
        area: size.width * size.height,
      };
    };
    const applyCandidate = (candidate) => {
      resetCandidateStyles();
      setPlacement(candidate.placement);
      applyCandidateWidth(candidate);
    };

    let selectedCandidate = null;
    if (isSingleColumn) {
      selectedCandidate = measureCandidate("after-authors");
    } else {
      const beforeWidth = getSafeBeforeAuthorsWidth();
      const candidates = [];
      const beforeCandidate = measureCandidate("before-authors", beforeWidth ? { fixedWidth: beforeWidth } : {});
      const afterAuthorsCandidate = measureCandidate("after-authors");
      const afterMetaCandidate = meta ? measureCandidate("after-meta") : null;

      [beforeCandidate, afterAuthorsCandidate, afterMetaCandidate].forEach((candidate) => {
        if (candidate) {
          candidates.push(candidate);
        }
      });
      selectedCandidate = candidates.reduce((best, candidate) => {
        if (!best || candidate.area > best.area) {
          return candidate;
        }
        return best;
      }, null);
    }

    if (!selectedCandidate) {
      selectedCandidate = { placement: meta ? "after-meta" : "after-authors" };
    }
    applyCandidate(selectedCandidate);

    const shouldPlaceAfterAuthors = selectedCandidate.placement !== "before-authors";

    if (!logoRow) {
      revealCluster();
      return;
    }

    window.requestAnimationFrame(() => {
      try {
        const imageBox = image.getBoundingClientRect();
        const logoBox = logoRow.getBoundingClientRect();
        const availableHeight = Math.floor(logoBox.bottom - imageBox.top - 1);
        const canGrowLandscapeToLogo =
          shouldPlaceAfterAuthors &&
          (item.classList.contains("publication__item--text-figure-only") || videoCount <= 1) &&
          isLandscapeFigure;
        const canGrowPortraitToLogo =
          !shouldPlaceAfterAuthors &&
          (videoCount > 1 || item.classList.contains("publication__item--text-figure-only")) &&
          isPortraitFigure;
        const canGrowToLogo = canGrowLandscapeToLogo || canGrowPortraitToLogo;

        if (canGrowToLogo && availableHeight > imageBox.height + 1) {
          image.style.maxHeight = `${availableHeight}px`;
        }

        const adjustedImageBox = image.getBoundingClientRect();
        const finalAvailableHeight = Math.floor(logoBox.bottom - adjustedImageBox.top - 1);
        if (finalAvailableHeight <= 0) {
          return;
        }

        if (adjustedImageBox.height > finalAvailableHeight) {
          image.style.maxHeight = `${finalAvailableHeight}px`;
          return;
        }

        const overflow = adjustedImageBox.bottom - logoBox.bottom;
        if (overflow <= 1) {
          return;
        }

        const nextHeight = Math.max(48, Math.floor(adjustedImageBox.height - overflow - 1));
        image.style.maxHeight = `${nextHeight}px`;
      } finally {
        revealCluster();
      }
    });
  };

  const layoutAll = () => {
    items.forEach(layoutItem);
  };

  let resizeTimer = null;
  const scheduleLayout = () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(layoutAll, 80);
  };

  layoutAll();
  window.addEventListener("resize", scheduleLayout);
  items.forEach((item) => {
    const image = item.querySelector(".publication__visual-cluster img");
    if (image && !image.complete) {
      image.addEventListener("load", scheduleLayout, { once: true });
    }
  });
};

let initPublicationAuthorNameWrap = () => {
  const authorBlocks = document.querySelectorAll(".publication__authors");
  authorBlocks.forEach((block) => {
    if (block.dataset.namesWrapped === "true") {
      return;
    }

    const parts = block.innerHTML.split(/(,\s+|\s+and\s+)/i);
    block.innerHTML = parts.map((part) => {
      if (!part.trim() || /^,\s+$/.test(part) || /^\s+and\s+$/i.test(part)) {
        return part;
      }
      const leading = part.match(/^\s*/)[0];
      const trailing = part.match(/\s*$/)[0];
      const name = part.trim();
      const conjunctionMatch = name.match(/^and\s+/i);
      if (conjunctionMatch) {
        const conjunction = conjunctionMatch[0];
        return `${leading}${conjunction}<span class="publication__author-name">${name.slice(conjunction.length)}</span>${trailing}`;
      }
      return `${leading}<span class="publication__author-name">${name}</span>${trailing}`;
    }).join("");
    block.dataset.namesWrapped = "true";
  });
};

let initCvEducationLayout = () => {
  const groups = document.querySelectorAll(".cv-education");
  if (groups.length === 0) {
    return;
  }

  const measureTextWidth = (body) => {
    const bodyBox = body.getBoundingClientRect();
    const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        return node.textContent.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      },
    });
    let maxTextRight = bodyBox.left;
    let hasText = false;

    while (walker.nextNode()) {
      const range = document.createRange();
      range.selectNodeContents(walker.currentNode);
      Array.from(range.getClientRects()).forEach((rect) => {
        if (rect.width > 1 && rect.height > 1) {
          hasText = true;
          maxTextRight = Math.max(maxTextRight, rect.right);
        }
      });
    }

    if (!hasText) {
      return bodyBox.width;
    }
    return maxTextRight - bodyBox.left;
  };

  const layoutAll = () => {
    const isSingleColumn = window.matchMedia("(max-width: 520px)").matches;
    groups.forEach((group) => {
      group.style.removeProperty("--cv-education-body-width");
      if (isSingleColumn) {
        return;
      }

      const items = Array.from(group.querySelectorAll(".cv-education__item"));
      const logos = Array.from(group.querySelectorAll(".cv-education__logo-link"));
      if (items.length === 0 || logos.length === 0) {
        return;
      }

      const maxTextWidth = Math.max(...items.map((item) => measureTextWidth(item.querySelector(".cv-education__body"))));
      const columnGap = parseFloat(window.getComputedStyle(items[0]).columnGap) || 0;
      const maxLogoWidth = Math.max(...logos.map((logo) => logo.getBoundingClientRect().width));
      const maxBodyWidth = group.getBoundingClientRect().width - maxLogoWidth - columnGap;
      if (maxBodyWidth <= 0) {
        return;
      }

      group.style.setProperty("--cv-education-body-width", `${Math.ceil(Math.min(maxTextWidth, maxBodyWidth))}px`);
    });
  };

  let resizeTimer = null;
  const scheduleLayout = () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(layoutAll, 80);
  };

  layoutAll();
  window.addEventListener("resize", scheduleLayout);
  groups.forEach((group) => {
    group.querySelectorAll(".cv-education__logo").forEach((image) => {
      if (!image.complete) {
        image.addEventListener("load", scheduleLayout, { once: true });
      }
    });
  });
};

/* ==========================================================================
   Plotly integration script so that Markdown codeblocks will be rendered
   ========================================================================== */

// Read the Plotly data from the code block, hide it, and render the chart as new node. This allows for the 
// JSON data to be retrieve when the theme is switched. The listener should only be added if the data is 
// actually present on the page.
import { plotlyDarkLayout, plotlyLightLayout } from './theme.js';
let plotlyElements = document.querySelectorAll("pre>code.language-plotly");
if (plotlyElements.length > 0) {
  document.addEventListener("readystatechange", () => {
    if (document.readyState === "complete") {
      plotlyElements.forEach((elem) => {
        // Parse the Plotly JSON data and hide it
        var jsonData = JSON.parse(elem.textContent);
        elem.parentElement.classList.add("hidden");

        // Add the Plotly node
        let chartElement = document.createElement("div");
        elem.parentElement.after(chartElement);

        // Set the theme for the plot and render it
        const theme = (determineComputedTheme() === "dark") ? plotlyDarkLayout : plotlyLightLayout;
        if (jsonData.layout) {
          jsonData.layout.template = (jsonData.layout.template) ? { ...theme, ...jsonData.layout.template } : theme;
        } else {
          jsonData.layout = { template: theme };
        }
        Plotly.react(chartElement, jsonData.data, jsonData.layout);
      });
    }
  });
}

/* ==========================================================================
   Actions that should occur when the page has been fully loaded
   ========================================================================== */

$(document).ready(function () {
  // SCSS SETTINGS - These should be the same as the settings in the relevant files 
  const scssLarge = 925;          // pixels, from /_sass/_themes.scss
  const scssMastheadHeight = 70;  // pixels, from the current theme (e.g., /_sass/theme/_default.scss)

  // If the user hasn't chosen a theme, follow the OS preference
  setTheme();
  window.matchMedia('(prefers-color-scheme: dark)')
        .addEventListener("change", (e) => {
          if (!localStorage.getItem("theme")) {
            setTheme(e.matches ? "dark" : "light");
          }
        });

  // Enable the theme toggle
  $('#theme-toggle').on('click', toggleTheme);

  // Enable the sticky footer
  var bumpIt = function () {
    $("body").css("padding-bottom", "0");
    $("body").css("margin-bottom", "0");
  }
  $(window).resize(function () {
    didResize = true;
  });
  setInterval(function () {
    if (didResize) {
      didResize = false;
      bumpIt();
    }}, 250);
  var didResize = false;
  bumpIt();

  // FitVids init
  fitvids();

  initPublicationFigureDialogs();
  initCopyButtons();
  initPublicationAuthorNameWrap();
  initPublicationListLayout();
  initCvEducationLayout();

  // Follow menu drop down
  $(".author__urls-wrapper > .author__follow-button").on("click", function () {
    $(".author__urls").fadeToggle("fast", function () { });
    $(".author__urls-wrapper > .author__follow-button").toggleClass("open");
  });

  // Restore the follow menu if toggled on a window resize
  jQuery(window).on('resize', function () {
    if ($('.author__urls.social-icons').css('display') == 'none' && $(window).width() >= scssLarge) {
      $(".author__urls").css('display', 'block')
    }
  });

  // Init smooth scroll, this needs to be slightly more than then fixed masthead height
  $("a").smoothScroll({
    offset: -scssMastheadHeight,
    preventDefault: false,
  });

});
