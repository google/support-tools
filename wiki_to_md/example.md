# Header1

This is a test file for verifying the tool's output. You can regenerate
`example.md` yourself by running:

```
python wiki2gfm.py \
    --project=test \
    --wikipages_list="TestPage" \
    --input_file=example.wiki \
    --output_file=example.md
```

Note that this is used by {{wiki2gfm\_test.py}}, so changing the
arguments will break unit tests.



#### Tables (mistmatched header sides)

Paragraph.

More paragraphs.

Tables:

|**Name/Sample**   | **Markup**       |
|:-----------------|:-----------------|
|  _italic_        | `_italic_`       |
|  **bold**         | `*bold*`         |
|  `code`          | ```code```       |
|  `code`          | `{{{code}}}`     |
|  <sup>super</sup>script  | `^super^script`  |
|  <sub>sub</sub>script  | `,,sub,,script`  |
| ~~strikeout~~    | `~~strikeout~~`  |

You can mix these typefaces in some ways:

|       **Markup**                    |        **Result**                 |
|:------------------------------------|:----------------------------------|
| `_*bold* in italics_`               | _**bold** in italics_             |
| `*_italics_ in bold*`               | **_italics_ in bold**             |
| `*~~strike~~ works too*`            | **~~strike~~ works too**          |
| `~~as well as _this_ way round~~`   | ~~as well as _this_ way round~~   |

**IN HTML**

<span>
Tables:<br>
<br>
<table><thead><th><b>Name/Sample</b>   </th><th> <b>Markup</b>       </th></thead><tbody>
<tr><td>  <i>italic</i>       </td><td> <code>_italic_</code>       </td></tr>
<tr><td>  <b>bold</b>         </td><td> <code>*bold*</code>         </td></tr>
<tr><td>  <code>code</code>         </td><td> <code>`code`</code>     </td></tr>
<tr><td>  <code>code</code>     </td><td> <code>{{{code}}}</code>     </td></tr>
<tr><td>  <sup>super</sup>script  </td><td> <code>^super^script</code>  </td></tr>
<tr><td>  <sub>sub</sub>script  </td><td> <code>,,sub,,script</code>  </td></tr>
<tr><td> <del>strikeout</del>   </td><td> <code>~~strikeout~~</code>  </td></tr></tbody></table>

You can mix these typefaces in some ways:<br>
<br>
<table><thead><th>       <b>Markup</b>                    </th><th>        <b>Result</b>                 </th></thead><tbody>
<tr><td> <code>_*bold* in italics_</code>             </td><td> <i><b>bold</b> in italics</i>             </td></tr>
<tr><td> <code>*_italics_ in bold*</code>             </td><td> <b><i>italics</i> in bold</b>             </td></tr>
<tr><td> <code>*~~strike~~ works too*</code>          </td><td> <b><del>strike</del> works too</b>          </td></tr>
<tr><td> <code>~~as well as _this_ way round~~</code> </td><td> <del>as well as <i>this</i> way round</del> </td></tr>
</span></tbody></table>

#### Code (mismatched header sides again)

```
{{{
def fib(n):
  if n == 0 or n == 1:
    return n
  else:
    # This recursion is not good for large numbers.
    return fib(n-1) + fib(n-2)
}}}
```

Which results in:

```
def fib(n):
  if n == 0 or n == 1:
    return n
  else:
    # This recursion is not good for large numbers.
    return fib(n-1) + fib(n-2)
```

```
<code language="xml">
<hello target="world"/>
</code>
```

```xml

<hello target="world"/>
```

**IN HTML**

<span>
<pre><code>{{{<br>
def fib(n):<br>
  if n == 0 or n == 1:<br>
    return n<br>
  else:<br>
    # This recursion is not good for large numbers.<br>
    return fib(n-1) + fib(n-2)<br>
}}}<br>
</code></pre>

Which results in:<br>
<br>
<pre><code>def fib(n):<br>
  if n == 0 or n == 1:<br>
    return n<br>
  else:<br>
    # This recursion is not good for large numbers.<br>
    return fib(n-1) + fib(n-2)<br>
</code></pre>

<pre><code>&lt;code language="xml"&gt;<br>
&lt;hello target="world"/&gt;<br>
&lt;/code&gt;<br>
</code></pre>

<pre><code><br>
&lt;hello target="world"/&gt;<br>
</code></pre>
</span>

==== Lists

The following is:
  * A list
  * Of bulleted items
    1. This is a numbered sublist
    1. Which is done by indenting further
  * And back to the main bulleted list

  * This is also a list
  * With a single leading space
  * Notice that it is rendered
    1. At the same levels
    1. As the above lists.
  * Despite the different indentation levels.

> Blockquotes are seen as lists. Time to nest:
> > Nested!

> Okay back.

**IN HTML**

<span>
The following is:<br>
<ul><li>A list<br>
</li><li>Of bulleted items<br>
<ol><li>This is a numbered sublist<br>
</li><li>Which is done by indenting further<br>
</li></ol></li><li>And back to the main bulleted list</li></ul>

<ul><li>This is also a list<br>
</li><li>With a single leading space<br>
</li><li>Notice that it is rendered<br>
<ol><li>At the same levels<br>
</li><li>As the above lists.<br>
</li></ol></li><li>Despite the different indentation levels.</li></ul>

<blockquote>Blockquotes are seen as lists. Time to nest:<br>
<blockquote>Nested!<br>
</blockquote>Okay back.<br>
</span></blockquote>

==== Links

A LittleLink[?](TestPage.md)

[TestPage](TestPage.md) is linked automatically.

http://www.google.com/

[Google home page](http://www.google.com)

[![](https://www.google.com/images/srpr/logo11w.png)](http://www.google.com)

![https://www.google.com/images/srpr/logo11w.png](https://www.google.com/images/srpr/logo11w.png)

[An image](https://www.google.com/images/srpr/logo11w.png)

![![](https://www.google.com/images/srpr/logo11w.png)](https://www.google.com/images/srpr/logo11w.png)

**IN HTML**

<span>
A LittleLink<a href='TestPage.md'>?</a>

<a href='TestPage.md'>TestPage</a> is linked automatically.<br>
<br>
<a href='http://www.google.com/'>http://www.google.com/</a>

<a href='http://www.google.com'>Google home page</a>

<a href='http://www.google.com'><img src='https://www.google.com/images/srpr/logo11w.png' /></a>

<img src='https://www.google.com/images/srpr/logo11w.png' />

<a href='https://www.google.com/images/srpr/logo11w.png'>An image</a>

<a href='https://www.google.com/images/srpr/logo11w.png'><img src='https://www.google.com/images/srpr/logo11w.png' /></a>
</span>

==== Issues

This is [issue 123](https://code.google.com/p/test/issues/detail?id=123), auto-linked.
This would be [issue 456](https://code.google.com/p/test/issues/detail?id=456), but must link to old one.

**IN HTML**

This is [issue 123](https://code.google.com/p/test/issues/detail?id=123), auto-linked.
This would be [issue 456](https://code.google.com/p/test/issues/detail?id=456), but must link to old one.

==== Revisions

[Revision 111605](https://code.google.com/p/test/source/detail?r=111605).

rev111612.

**IN HTML**

<span>
<a href='https://code.google.com/p/test/source/detail?r=111605'>Revision 111605</a>.<br>
<br>
rev111612.<br>
</span>

==== Plugins

<a href='Hidden comment: 
This text will be removed from the rendered page.
'></a>



<a href='http://www.youtube.com/watch?feature=player_embedded&v=FiARsQSlzDc' target='_blank'><img src='http://img.youtube.com/vi/FiARsQSlzDc/0.jpg' width='425' height=344 /></a>

<span>
<a href='Hidden comment: 
This text will be removed from the rendered page.
'></a><br>
<br>
<br>
<br>
<a href='http://www.youtube.com/watch?feature=player_embedded&v=FiARsQSlzDc' target='_blank'><img src='http://img.youtube.com/vi/FiARsQSlzDc/0.jpg' width='425' height=344 /></a><br>
</span>

==== Variables

%%notdefined%%

(TODO: Replace with username.)

(TODO: Replace with email address.)

test

**IN HTML** (with additional variable magic)

<span>
%%notdefined%%<br>
<br>
(TODO: Replace with username.)<br>
<br>
(TODO: Replace with email address.)<br>
<br>
test<br>
<br>
this is a var!<br>
</span>


## All done!

Hope you enjoyed.

# Regressions

We were adding extra spaces around tick marks:

alpha `beta` gamma
