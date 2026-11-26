"""Optional instrumentation at the converter's final bullet text boundary."""


def annotate_bullet(raw, rendered, config=None, *, protect_item=False):
    hook = (config or {}).get("_bullet_probe")
    result = hook(raw, rendered) if hook else rendered
    # A leading '[' must be text, not the optional label argument to \item.
    return "{" + result + "}" if protect_item and raw.lstrip().startswith("[") else result


def annotate_summary(raw, rendered, config=None):
    hook = (config or {}).get("_summary_probe")
    return hook(raw, rendered) if hook else rendered


PROBE_SETUP = r"""
\newsavebox{\ResumeFitBox}
\newcount\ResumeFitLines
\newcommand{\ResumeFitProbe}[2]{%
  \begingroup
  \sbox{\ResumeFitBox}{#2}%
  \typeout{RF-W:#1:\the\wd\ResumeFitBox:\the\linewidth}%
  \setbox\ResumeFitBox=\vbox{%
    \hsize=\linewidth\parshape=0\hangindent=0pt\leftskip=0pt
    \noindent #2\par\global\ResumeFitLines=\prevgraf}%
  \typeout{RF-L:#1:\the\ResumeFitLines}%
  \endgroup
  \begingroup\leavevmode\pdflinkmargin=0pt
  \pdfstartlink attr{/Border[0 0 0]} user{%
    /Subtype /Link /A << /S /URI /URI (resumefit:#1) >>}%
  #2\pdfendlink\endgroup}
"""
