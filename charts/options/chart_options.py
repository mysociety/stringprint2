from .base import OptionObject,Choice,Option

class GridlinesOption(OptionObject):
    color = Option(type = "string",
                   default = "#CCC",
                   description = "The color of the horizontal gridlines inside the chart area. Specify a valid HTML color string.")
    count = Option(type = "number",
                   default = 5,
                   description = "The number of horizontal gridlines inside the chart area. Minimum value is 2. Specify -1 to automatically compute the number of gridlines.")
    units = Option(type = "object",
                   default = "null",
                   description = "Overrides the default format for various aspects of date/datetime/timeofday data types when used with chart computed gridlines. Allows formatting for years, months, days, hours, minutes, seconds, and milliseconds.")

class MinorGridlinesOption(OptionObject):
    color = Option(type = "string",
                   description = "The color of the horizontal minor gridlines inside the chart area. Specify a valid HTML color string.")
    count = Option(type = "number",
                   default = 0,
                   description = "The number of horizontal minor gridlines between two regular gridlines.")
    units = Option(type = "object",
                   default = "null",
                   description = "Overrides the default format for various aspects of date/datetime/timeofday data types when used with chart computed minorGridlines. Allows formatting for years, months, days, hours, minutes, seconds, and milliseconds.")

class ViewWindowOption(OptionObject):
    max = Option(type = "number",
                 default = "auto")
    min = Option(type = "number",
                 default = "auto")

class NOption(OptionObject):
    color = Option(type = "string",
                   description = "The color of thetrendline, expressed as either an English color name or a hex string.")
    degree = Option(type = "number",
                    default = 3,
                    description = "Fortrendlinesoftype: 'polynomial', the degree of the polynomial (2for quadratic,3for cubic, and so on). (The default degree may change from 3 to 2 in an upcoming release of Google Charts.)")
    labelInLegend = Option(type = "string",
                           default = "null",
                           description = "If set, thetrendlinewill appear in the legend as this string.")
    lineWidth = Option(type = "number",
                       default = 2,
                       description = "The line width of thetrendline, in pixels.")
    opacity = Option(type = "number",
                     default = "1.0",
                     description = "The transparency of thetrendline, from 0.0 (transparent) to 1.0 (opaque).")
    pointSize = Option(type = "number",
                       default = 1,
                       description = "Trendlinesare constucted by stamping a bunch of dots on the chart; this rarely-needed option lets you customize the size of the dots. The trendline'slineWidthoption will usually be preferable. However, you'll need this option if you're using the globalpointSizeoption and want a different point size for your trendlines.")
    pointsVisible = Option(type = "boolean",
                           default = "true",
                           description = "Trendlinesare constucted by stamping a bunch of dots on the chart. The trendline'spointsVisibleoption determines whether the points for a particular trendline are visible.")
    showR2 = Option(type = "boolean",
                    default = "false",
                    description = "Whether to show thecoefficient of determinationin the legend or trendline tooltip.")
    type = Option(type = "string",
                  default = "linear",
                  description = "Whether thetrendlinesis'linear'(the default),'exponential', or'polynomial'.")
    visibleInLegend = Option(type = "boolean",
                             default = "false",
                             description = "Whether thetrendlineequation appears in the legend. (It will appear in the trendline tooltip.)")

class AnimationOption(OptionObject):
    duration = Option(type = "number",
                      default = 0,
                      description = "The duration of the animation, in milliseconds. For details, see theanimation documentation.")
    startup = Option(type = "boolean",
                     description = "Determines if the chart will animate on the initial draw. Iftrue, the chart will start at the baseline and animate to its final state.")
    easing = Option(type = "string",
                    default = "linear",
                    description = "The easing function applied to the animation. The following options are available:",
                    choices = (Choice("linear","Constant speed."),
                               Choice("in","Ease in - Start slow and speed up."),
                               Choice("out","Ease out - Start fast and slow down."),
                               Choice("inAndOut","Ease in and out - Start slow, speed up, then slow down."),))

class AnnotationsOption(OptionObject):
    boxStyle = Option(type = "object",
                      default = "null",
                      description = "For charts that supportannotations, theannotations.boxStyleobject controls the appearance of the boxes surrounding annotations:")
    datum = Option(type = "object",
                   description = "For charts that supportannotations, theannotations.datumobject lets you override Google Charts' choice for annotations provided for individual data elements (such as values displayed with each bar on a bar chart). You can control the color withannotations.datum.stem.color, the stem length withannotations.datum.stem.length, and the style withannotations.datum.style.")
    domain = Option(type = "object",
                    description = "For charts that supportannotations, theannotations.domainobject lets you override Google Charts' choice for annotations provided for a domain (the major axis of the chart, such as the X axis on a typical line chart). You can control the color withannotations.domain.stem.color, the stem length withannotations.domain.stem.length, and the style withannotations.domain.style.")
    highContrast = Option(type = "boolean",
                          default = "true",
                          description = "For charts that supportannotations, theannotations.highContrastboolean lets you override Google Charts' choice of the annotation color. By default,annotations.highContrastis true, which causes Charts to select an annotation color with good contrast: light colors on dark backgrounds, and dark on light. If you setannotations.highContrastto false and don't specify your own annotation color, Google Charts will use the default series color for the annotation:")
    stem = Option(type = "object",
                  description = "For charts that supportannotations, theannotations.stemobject lets you override Google Charts' choice for the stem style. You can control color withannotations.stem.colorand the stem length withannotations.stem.length. Note that the stem length option has no effect on annotations with style'line': for'line'datum annotations, the stem length is always the same as the text, and for'line'domain annotations, the stem extends across the entire chart.")
    style = Option(type = "string",
                   default = "point",
                   description = "For charts that supportannotations, theannotations.styleoption lets you override Google Charts' choice of the annotation type. It can be either'line'or'point'.")
    textStyle = Option(type = "object",
                       default = "null",
                       description = "For charts that supportannotations, theannotations.textStyleobject controls the appearance of the text of the annotation:")

class BackgroundColorOption(OptionObject):
    stroke = Option(type = "string",
                    default = "#666",
                    description = "The color of the chart border, as an HTML color string.")
    strokeWidth = Option(type = "number",
                         default = 0,
                         description = "The border width, in pixels.")
    fill = Option(type = "string",
                  default = "white",
                  description = "The chart fill color, as an HTML color string.")

class ChartAreaOption(OptionObject):
    backgroundColor = Option(type = "string or object",
                             default = "white",
                             description = "Chart area background color. When a string is used, it can be either a hex string (e.g., '#fdc') or an English color name. When an object is used, the following properties can be provided:",
                             choices = (Choice("stroke","the color, provided as a hex string or English color name."),
                                        Choice("strokeWidth","if provided, draws a border around the chart area of the given width (and with the color ofstroke)."),))
    left = Option(type = "number or string",
                  default = "auto",
                  description = "How far to draw the chart from the left border.")
    top = Option(type = "number or string",
                 default = "auto",
                 description = "How far to draw the chart from the top border.")
    width = Option(type = "number or string",
                   default = "auto",
                   description = "Chart area width.")
    height = Option(type = "number or string",
                    default = "auto",
                    description = "Chart area height.")

class CrosshairOption(OptionObject):
    color = Option(type = "default",
                   description = "The crosshair color, expressed as either a color name (e.g., 'blue') or an RGB value (e.g., '#adf').")
    focused = Option(type = "object",
                     default = "default",
                     description = "An object containing the crosshair properties upon focus.Example:crosshair: { focused: { color: '#3bc', opacity: 0.8 } }")
    opacity = Option(type = "number",
                     default = "1.0",
                     description = "The crosshair opacity, with0.0being fully transparent and1.0fully opaque.")
    orientation = Option(type = "string",
                         default = "both",
                         description = "The crosshair orientation, which can be 'vertical' for vertical hairs only, 'horizontal' for horizontal hairs only, or 'both' for traditional crosshairs.")
    selected = Option(type = "object",
                      default = "default",
                      description = "An object containing the crosshair properties upon selection.Example:crosshair: { selected: { color: '#3bc', opacity: 0.8 } }")
    trigger = Option(type = "string",
                     default = "both",
                     description = "When to display crosshairs: on'focus','selection', or'both'.")

class ExplorerOption(OptionObject):
    actions = Option(type = "Array of strings",
                     description = "The Google Charts explorer supports three actions:",
                     choices = (Choice("dragToPan","Drag to pan around the chart horizontally and vertically. To pan only along the horizontal axis, useexplorer: { axis: 'horizontal' }. Similarly for the vertical axis."),
                                Choice("dragToZoom","The explorer's default behavior is to zoom in and out when the user scrolls. Ifexplorer: { actions: ['dragToZoom', 'rightClickToReset'] }is used, dragging across a rectangular area zooms into that area. We recommend usingrightClickToResetwheneverdragToZoomis used. Seeexplorer.maxZoomIn,explorer.maxZoomOut, andexplorer.zoomDeltafor zoom customizations."),
                                Choice("rightClickToReset","Right clicking on the chart returns it to the original pan and zoom level."),))
    axis = Option(type = "string",
                  description = "By default, users can pan both horizontally and vertically when theexploreroption is used. If you want to users to only pan horizontally, useexplorer: { axis: 'horizontal' }. Similarly,explorer: { axis: 'vertical' }enables vertical-only panning.")
    keepInBounds = Option(type = "boolean",
                          default = "false",
                          description = "By default, users can pan all around, regardless of where the data is. To ensure that users don't pan beyond the original chart, useexplorer: { keepInBounds: true }.")
    maxZoomIn = Option(type = "number",
                       default = "0.25",
                       description = "The maximum that the explorer can zoom in. By default, users will be able to zoom in enough that they'll see only 25% of the original view. Settingexplorer: { maxZoomIn: .5 }would let users zoom in only far enough to see half of the original view.")
    maxZoomOut = Option(type = "number",
                        default = 4,
                        description = "The maximum that the explorer can zoom out. By default, users will be able to zoom out far enough that the chart will take up only 1/4 of the available space. Settingexplorer: { maxZoomOut: 8 }would let users zoom out far enough that the chart would take up only 1/8 of the available space.")
    zoomDelta = Option(type = "number",
                       default = "1.5",
                       description = "When users zoom in or out,explorer.zoomDeltadetermines how much they zoom by. The smaller the number, the smoother and slower the zoom.")

class HAxisOption(OptionObject):
    gridlines = GridlinesOption
    minorGridlines = MinorGridlinesOption
    viewWindow = ViewWindowOption
    baseline = Option(type = "number",
                      default = "automatic",
                      description = "The baseline for the horizontal axis.")
    baselineColor = Option(type = "number",
                           default = "black",
                           description = "The color of the baseline for the horizontal axis. Can be any HTML color string, for example:'red'or'#00cc00'.")
    direction = Option(type = "1 or -1",
                       default = 1,
                       description = "The direction in which the values along the horizontal axis grow. Specify-1to reverse the order of the values.")
    format = Option(type = "string",
                    default = "auto",
                    description = "A format string for numeric or date axis labels.",
                    choices = (Choice("none","displays numbers with no formatting (e.g., 8000000)"),
                               Choice("decimal","displays numbers with thousands separators (e.g., 8,000,000)"),
                               Choice("scientific","displays numbers in scientific notation (e.g., 8e6)"),
                               Choice("currency","displays numbers in the local currency (e.g., $8,000,000.00)"),
                               Choice("percent","displays numbers as percentages (e.g., 800,000,000%)"),
                               Choice("short","displays abbreviated numbers (e.g., 8M)"),
                               Choice("long","displays numbers as full words (e.g., 8 million)"),))
    logScale = Option(type = "boolean",
                      default = "false",
                      description = "hAxisproperty that makes the horizontal axis a logarithmic scale (requires all values to be positive). Set to true for yes.")
    scaleType = Option(type = "string",
                       default = "null",
                       description = "hAxisproperty that makes the horizontal axis a logarithmic scale. Can be one of the following:",
                       choices = (Choice("null","No logarithmic scaling is performed."),
                                  Choice("log","Logarithmic scaling. Negative and zero values are not plotted. This option is the same as settinghAxis: { logscale: true }."),
                                  Choice("mirrorLog","Logarithmic scaling in which negative and zero values are plotted. The plotted value of a negative number is the negative of the log of the absolute value. Values close to 0 are plotted on a linear scale."),))
    textPosition = Option(type = "string",
                          default = "out",
                          description = "Position of the horizontal axis text, relative to the chart area. Supported values: 'out', 'in', 'none'.")
    textStyle = Option(type = "object",
                       default = "{color",
                       description = "An object that specifies the horizontal axis text style. The object has this format:")
    ticks = Option(type = "Array of elements",
                   default = "auto",
                   description = "Replaces the automatically generated X-axis ticks with the specified array. Each element of the array should be either a valid tick value (such as a number, date, datetime, or timeofday), or an object. If it's an object, it should have avproperty for the tick value, and an optionalfproperty containing the literal string to be displayed as the label.",
                   choices = (Choice("hAxis","{ ticks: [5,10,15,20] }"),
                              Choice("hAxis","{ ticks: [{v:32, f:'thirty two'}, {v:64, f:'sixty four'}] }"),
                              Choice("hAxis","{ ticks: [new Date(2014,3,15), new Date(2013,5,15)] }"),
                              Choice("hAxis","{ ticks: [16, {v:32, f:'thirty two'}, {v:64, f:'sixty four'}, 128] }"),))
    title = Option(type = "string",
                   default = "null",
                   description = "hAxisproperty that specifies the title of the horizontal axis.")
    titleTextStyle = Option(type = "object",
                            default = "{color",
                            description = "An object that specifies the horizontal axis title text style. The object has this format:")
    allowContainerBoundaryTextCufoff = Option(type = "boolean",
                                              default = "false",
                                              description = "If false, will hide outermost labels rather than allow them to be cropped by the chart container. If true, will allow label cropping.")
    slantedText = Option(type = "boolean",
                         default = "automatic",
                         description = "If true, draw the horizontal axis text at an angle, to help fit more text along the axis; if false, draw horizontal axis text upright. Default behavior is to slant text if it cannot all fit when drawn upright. Notice that this option is available only when thehAxis.textPositionis set to 'out' (which is the default).")
    slantedTextAngle = Option(type = "number, 1&mdash;90",
                              default = 30,
                              description = "The angle of the horizontal axis text, if it's drawn slanted. Ignored ifhAxis.slantedTextisfalse, or is in auto mode, and the chart decided to draw the text horizontally.")
    maxAlternation = Option(type = "number",
                            default = 2,
                            description = "Maximum number of levels of horizontal axis text. If axis text labels become too crowded, the server might shift neighboring labels up or down in order to fit labels closer together. This value specifies the most number of levels to use; the server can use fewer levels, if labels can fit without overlapping.")
    maxTextLines = Option(type = "number",
                          default = "auto",
                          description = "Maximum number of lines allowed for the text labels. Labels can span multiple lines if they are too long, and the nuber of lines is, by default, limited by the height of the available space.")
    minTextSpacing = Option(type = "number",
                            description = "Minimum horizontal spacing, in pixels, allowed between two adjacent text labels. If the labels are spaced too densely, or they are too long, the spacing can drop below this threshold, and in this case one of the label-unclutter measures will be applied (e.g, truncating the lables or dropping some of them).")
    showTextEvery = Option(type = "number",
                           default = "automatic",
                           description = "How many horizontal axis labels to show, where 1 means show every label, 2 means show every other label, and so on. Default is to try to show as many labels as possible without overlapping.")
    maxValue = Option(type = "number",
                      default = "automatic",
                      description = "Moves the max value of the horizontal axis to the specified value; this will be rightward in most charts. Ignored if this is set to a value smaller than the maximum x-value of the data.hAxis.viewWindow.maxoverrides this property.")
    minValue = Option(type = "number",
                      default = "automatic",
                      description = "Moves the min value of the horizontal axis to the specified value; this will be leftward in most charts. Ignored if this is set to a value greater than the minimum x-value of the data.hAxis.viewWindow.minoverrides this property.")
    viewWindowMode = Option(type = "string",
                            description = "Specifies how to scale the horizontal axis to render the values within the chart area. The following string values are supported:",
                            choices = (Choice("pretty","Scale the horizontal values so that the maximum and minimum data values are rendered a bit inside the left and right of the chart area. This will causehaxis.viewWindow.minandhaxis.viewWindow.maxto be ignored."),
                                       Choice("maximized","Scale the horizontal values so that the maximum and minimum data values touch the left and right of the chart area. This will causehaxis.viewWindow.minandhaxis.viewWindow.maxto be ignored."),
                                       Choice("explicit","A deprecated option for specifying the left and right scale values of the chart area. (Deprecated because it's redundant withhaxis.viewWindow.minandhaxis.viewWindow.max.) Data values outside these values will be cropped. You must specify anhAxis.viewWindowobject describing the maximum and minimum values to show."),))

class LegendOption(OptionObject):
    alignment = Option(type = "string",
                       default = "automatic",
                       description = "Alignment of the legend. Can be one of the following:",
                       choices = (Choice("start","Aligned to the start of the area allocated for the legend."),
                                  Choice("center","Centered in the area allocated for the legend."),
                                  Choice("end","Aligned to the end of the area allocated for the legend."),))
    maxLines = Option(type = "number",
                      default = 1,
                      description = "Maximum number of lines in the legend. Set this to a number greater than one to add lines to your legend. Note: The exact logic used to determine the actual number of lines rendered is still in flux.")
    position = Option(type = "string",
                      default = "right",
                      description = "Position of the legend. Can be one of the following:",
                      choices = (Choice("bottom","Below the chart."),
                                 Choice("left","To the left of the chart, provided the left axis has no series associated with it. So if you want the legend on the left, use the optiontargetAxisIndex: 1."),
                                 Choice("in","Inside the chart, by the top left corner."),
                                 Choice("none","No legend is displayed."),
                                 Choice("right","To the right of the chart. Incompatible with thevAxesoption."),
                                 Choice("top","Above the chart."),))
    textStyle = Option(type = "object",
                       default = "{color",
                       description = "An object that specifies the legend text style. The object has this format:")

class TooltipOption(OptionObject):
    ignoreBounds = Option(type = "boolean",
                          default = "false",
                          description = "If set totrue, allows the drawing of tooltips to flow outside of the bounds of the chart on all sides.")
    isHtml = Option(type = "boolean",
                    default = "false",
                    description = "If set to true, use HTML-rendered (rather than SVG-rendered) tooltips. SeeCustomizing Tooltip Contentfor more details.")
    showColorCode = Option(type = "boolean",
                           default = "automatic",
                           description = "If true, show colored squares next to the series information in the tooltip. The default is true whenfocusTargetis set to 'category', otherwise the default is false.")
    textStyle = Option(type = "object",
                       default = "{color",
                       description = "An object that specifies the tooltip text style. The object has this format:")
    trigger = Option(type = "string",
                     default = "focus",
                     description = "The user interaction that causes the tooltip to be displayed:",
                     choices = (Choice("focus","The tooltip will be displayed when the user hovers over the element."),
                                Choice("none","The tooltip will not be displayed."),
                                Choice("selection","The tooltip will be displayed when the user selects the element."),))

class VAxisOption(OptionObject):
    gridlines = GridlinesOption
    minorGridlines = MinorGridlinesOption
    viewWindow = ViewWindowOption
    baseline = Option(type = "number",
                      default = "automatic",
                      description = "vAxisproperty that specifies the baseline for the vertical axis. If the baseline is larger than the highest grid line or smaller than the lowest grid line, it will be rounded to the closest gridline.")
    baselineColor = Option(type = "number",
                           default = "black",
                           description = "Specifies the color of the baseline for the vertical axis. Can be any HTML color string, for example:'red'or'#00cc00'.")
    direction = Option(type = "1 or -1",
                       default = 1,
                       description = "The direction in which the values along the vertical axis grow. Specify-1to reverse the order of the values.")
    format = Option(type = "string",
                    default = "auto",
                    description = "A format string for numeric axis labels. This is a subset of theICU pattern set. For instance,{format:'#,###%'}will display values &quot;1,000%&quot;, &quot;750%&quot;, and &quot;50%&quot; for values 10, 7.5, and 0.5. You can also supply any of the following:",
                    choices = (Choice("none","displays numbers with no formatting (e.g., 8000000)"),
                               Choice("decimal","displays numbers with thousands separators (e.g., 8,000,000)"),
                               Choice("scientific","displays numbers in scientific notation (e.g., 8e6)"),
                               Choice("currency","displays numbers in the local currency (e.g., $8,000,000.00)"),
                               Choice("percent","displays numbers as percentages (e.g., 800,000,000%)"),
                               Choice("short","displays abbreviated numbers (e.g., 8M)"),
                               Choice("long","displays numbers as full words (e.g., 8 million)"),))
    logScale = Option(type = "boolean",
                      default = "false",
                      description = "If true, makes the vertical axis a logarithmic scale. Note: All values must be positive.")
    scaleType = Option(type = "string",
                       default = "null",
                       description = "vAxisproperty that makes the vertical axis a logarithmic scale. Can be one of the following:",
                       choices = (Choice("null","No logarithmic scaling is performed."),
                                  Choice("log","Logarithmic scaling. Negative and zero values are not plotted. This option is the same as settingvAxis: { logscale: true }."),
                                  Choice("mirrorLog","Logarithmic scaling in which negative and zero values are plotted. The plotted value of a negative number is the negative of the log of the absolute value. Values close to 0 are plotted on a linear scale."),))
    textPosition = Option(type = "string",
                          default = "out",
                          description = "Position of the vertical axis text, relative to the chart area. Supported values: 'out', 'in', 'none'.")
    textStyle = Option(type = "object",
                       default = "{color",
                       description = "An object that specifies the vertical axis text style. The object has this format:")
    ticks = Option(type = "Array of elements",
                   default = "auto",
                   description = "Replaces the automatically generated Y-axis ticks with the specified array. Each element of the array should be either a valid tick value (such as a number, date, datetime, or timeofday), or an object. If it's an object, it should have avproperty for the tick value, and an optionalfproperty containing the literal string to be displayed as the label.",
                   choices = (Choice("vAxis","{ ticks: [5,10,15,20] }"),
                              Choice("vAxis","{ ticks: [{v:32, f:'thirty two'}, {v:64, f:'sixty four'}] }"),
                              Choice("vAxis","{ ticks: [new Date(2014,3,15), new Date(2013,5,15)] }"),
                              Choice("vAxis","{ ticks: [16, {v:32, f:'thirty two'}, {v:64, f:'sixty four'}, 128] }"),))
    title = Option(type = "string",
                   description = "vAxisproperty that specifies a title for the vertical axis.")
    titleTextStyle = Option(type = "object",
                            default = "{color",
                            description = "An object that specifies the vertical axis title text style. The object has this format:")
    maxValue = Option(type = "number",
                      default = "automatic",
                      description = "Moves the max value of the vertical axis to the specified value; this will be upward in most charts. Ignored if this is set to a value smaller than the maximum y-value of the data.vAxis.viewWindow.maxoverrides this property.")
    minValue = Option(type = "number",
                      default = "null",
                      description = "Moves the min value of the vertical axis to the specified value; this will be downward in most charts. Ignored if this is set to a value greater than the minimum y-value of the data.vAxis.viewWindow.minoverrides this property.")
    viewWindowMode = Option(type = "string",
                            description = "Specifies how to scale the vertical axis to render the values within the chart area. The following string values are supported:",
                            choices = (Choice("pretty","Scale the vertical values so that the maximum and minimum data values are rendered a bit inside the top and bottom of the chart area. This will causevaxis.viewWindow.minandvaxis.viewWindow.maxto be ignored."),
                                       Choice("maximized","Scale the vertical values so that the maximum and minimum data values touch the top and bottom of the chart area. This will causevaxis.viewWindow.minandvaxis.viewWindow.maxto be ignored."),
                                       Choice("explicit","A deprecated option for specifying the top and bottom scale values of the chart area. (Deprecated because it's redundant withvaxis.viewWindow.minandvaxis.viewWindow.max. Data values outside these values will be cropped. You must specify avAxis.viewWindowobject describing the maximum and minimum values to show."),))

class LineChartOption(OptionObject):
    animation = AnimationOption
    annotations = AnnotationsOption
    backgroundColor = BackgroundColorOption
    chartArea = ChartAreaOption
    crosshair = CrosshairOption
    explorer = ExplorerOption
    hAxis = HAxisOption
    legend = LegendOption
    tooltip = TooltipOption
    vAxis = VAxisOption
    aggregationTarget = Option(type = "string",
                               default = "auto",
                               description = "How multiple data selections are rolled up into tooltips:",
                               choices = (Choice("category","Group selected data by x-value."),
                                          Choice("series","Group selected data by series."),
                                          Choice("auto","Group selected data by x-value if all selections have the same x-value, and by series otherwise."),
                                          Choice("none","Show only one tooltip per selection."),))
    axisTitlesPosition = Option(type = "string",
                                default = "out",
                                description = "Where to place the axis titles, compared to the chart area. Supported values:",
                                choices = (Choice("in","Draw the axis titles inside the the chart area."),
                                           Choice("out","Draw the axis titles outside the chart area."),
                                           Choice("none","Omit the axis titles."),))
    colors = Option(type = "Array of strings",
                    description = "The colors to use for the chart elements. An array of strings, where each element is an HTML color string, for example:colors:&#91;'red','#004411'].")
    curveType = Option(type = "string",
                       default = "none",
                       description = "Controls the curve of the lines when the line width is not zero. Can be one of the following:",
                       choices = (Choice("none","Straight lines without curve."),
                                  Choice("function","The angles of the line will be smoothed."),))
    dataOpacity = Option(type = "number",
                         default = "1.0",
                         description = "The transparency of data points, with 1.0 being completely opaque and 0.0 fully transparent. In scatter, histogram, bar, and column charts, this refers to the visible data: dots in the scatter chart and rectangles in the others. In charts whereselecting datacreates a dot, such as the line and area charts, this refers to the circles that appear upon hover or selection. The combo chart exhibits both behaviors, and this option has no effect on other charts. (To change the opacity of a trendline, seetrendline opacity.)")
    enableInteractivity = Option(type = "boolean",
                                 default = "true",
                                 description = "Whether the chart throws user-based events or reacts to user interaction. If false, the chart will not throw 'select' or other interaction-based events (butwillthrow ready or error events), and will not display hovertext or otherwise change depending on user input.")
    focusTarget = Option(type = "string",
                         default = "datum",
                         description = "The type of the entity that receives focus on mouse hover. Also affects which entity is selected by mouse click, and which data table element is associated with events. Can be one of the following:",
                         choices = (Choice("datum","Focus on a single data point. Correlates to a cell in the data table."),
                                    Choice("category","Focus on a grouping of all data points along the major axis. Correlates to a row in the data table."),))
    fontSize = Option(type = "number",
                      default = "automatic",
                      description = "The default font size, in pixels, of all text in the chart. You can override this using properties for specific chart elements.")
    fontName = Option(type = "string",
                      default = "Arial",
                      description = "The default font face for all text in the chart. You can override this using properties for specific chart elements.")
    forceIFrame = Option(type = "boolean",
                         default = "false",
                         description = "Draws the chart inside an inline frame. (Note that on IE8, this option is ignored; all IE8 charts are drawn in i-frames.)")
    height = Option(type = "number",
                    description = "Height of the chart, in pixels.")
    interpolateNulls = Option(type = "boolean",
                              default = "false",
                              description = "Whether to guess the value of missing points. If true, it will guess the value of any missing data based on neighboring points. If false, it will leave a break in the line at the unknown point.")
    lineDashStyle = Option(type = "Array of numbers",
                           default = "null",
                           description = "The on-and-off pattern for dashed lines. For instance,[4, 4]will repeat 4-length dashes followed by 4-length gaps, and[5, 1, 3]will repeat a 5-length dash, a 1-length gap, a 3-length dash, a 5-length gap, a 1-length dash, and a 3-length gap. SeeDashed Linesfor more information.")
    lineWidth = Option(type = "number",
                       default = 2,
                       description = "Data line width in pixels. Use zero to hide all lines and show only the points. You can override values for individual series using theseriesproperty.")
    orientation = Option(type = "string",
                         default = "horizontal",
                         description = "The orientation of the chart. When set to'vertical', rotates the axes of the chart so that (for instance) a column chart becomes a bar chart, and an area chart grows rightward instead of up:")
    pointShape = Option(type = "string",
                        default = "circle",
                        description = "The shape of individual data elements: 'circle', 'triangle', 'square', 'diamond', 'star', or 'polygon'. Seethe points documentationfor examples.")
    pointSize = Option(type = "number",
                       default = 0,
                       description = "Diameter of displayed points in pixels. Use zero to hide all points. You can override values for individual series using theseriesproperty. If you're using atrendline, thepointSizeoption will affect the width of the trendline unless you override it with thetrendlines.n.pointsizeoption.")
    pointsVisible = Option(type = "boolean",
                           default = "true",
                           description = "Determines whether points will be displayed. Set tofalseto hide all points. You can override values for individual series using theseriesproperty. If you're using atrendline, thepointsVisibleoption will affect the visibility of the points on all trendlines unless you override it with thetrendlines.n.pointsVisibleoption.")
    reverseCategories = Option(type = "boolean",
                               default = "false",
                               description = "If set to true, will draw series from right to left. The default is to draw left-to-right.")
    selectionMode = Option(type = "string",
                           default = "single",
                           description = "WhenselectionModeis'multiple', users may select multiple data points.")
    series = Option(type = "Array of objects, or object with nested objects",
                    default = "{}",
                    description = "An array of objects, each describing the format of the corresponding series in the chart. To use default values for a series, specify an empty object {}. If a series or a value is not specified, the global value will be used. Each object supports the following properties:",
                    choices = (Choice("annotations","An object to be applied to annotations for this series. This can be used to control, for instance, thetextStylefor the series:series: { 0: { annotations: { textStyle: {fontSize: 12, color: 'red' } } }}See the variousannotationsoptions for a more complete list of what can be customized."),
                               Choice("color","The color to use for this series. Specify a valid HTML color string."),
                               Choice("curveType","Overrides the globalcurveTypevalue for this series."),
                               Choice("labelInLegend","The description of the series to appear in the chart legend."),
                               Choice("lineDashStyle","Overrides the globallineDashStylevalue for this series."),
                               Choice("lineWidth","Overrides the globallineWidthvalue for this series."),
                               Choice("pointShape","Overrides the globalpointShapevalue for this series."),
                               Choice("pointSize","Overrides the globalpointSizevalue for this series."),
                               Choice("pointsVisible","Overrides the globalpointsVisiblevalue for this series."),
                               Choice("targetAxisIndex","Which axis to assign this series to, where 0 is the default axis, and 1 is the opposite axis. Default value is 0; set to 1 to define a chart where different series are rendered against different axes. At least one series much be allocated to the default axis. You can define a different scale for different axes."),
                               Choice("visibleInLegend","A boolean value, where true means that the series should have a legend entry, and false means that it should not. Default is true."),))
    theme = Option(type = "string",
                   default = "null",
                   description = "A theme is a set of predefined option values that work together to achieve a specific chart behavior or visual effect. Currently only one theme is available:",
                   choices = (Choice("maximized","Maximizes the area of the chart, and draws the legend and all of the labels inside the chart area. Sets the following options:chartArea: {width: '100%', height: '100%'},legend: {position: 'in'},titlePosition: 'in', axisTitlesPosition: 'in',hAxis: {textPosition: 'in'}, vAxis: {textPosition: 'in'}"),))
    title = Option(type = "string",
                   description = "Text to display above the chart.")
    titlePosition = Option(type = "string",
                           default = "out",
                           description = "Where to place the chart title, compared to the chart area. Supported values:",
                           choices = (Choice("in","Draw the title inside the chart area."),
                                      Choice("out","Draw the title outside the chart area."),
                                      Choice("none","Omit the title."),))
    titleTextStyle = Option(type = "object",
                            default = "{color",
                            description = "An object that specifies the title text style. The object has this format:")
    trendlines = Option(type = "object",
                        default = "null",
                        description = "Displaystrendlineson the charts that support them. By default, linear trendlines are used, but this can be customized with thetrendlines.n.typeoption.")
    vAxes = Option(type = "Array of object, or object with child objects",
                   default = "null",
                   description = "Specifies properties for individual vertical axes, if the chart has multiple vertical axes. Each child object is avAxisobject, and can contain all the properties supported byvAxis. These property values override any global settings for the same property.")
    width = Option(type = "number",
                   description = "Width of the chart, in pixels.")
    
