#if GRASSHOPPER_SDK
using System.Drawing;
using System.Drawing.Drawing2D;
using DG.Core.Mapping;
using Grasshopper;
using Grasshopper.GUI.Canvas;
using Grasshopper.Kernel;

namespace DG.Grasshopper.Mapping;

/// <summary>
/// Temporary frames and tags around the canvas components a mapping session proposes (plan 1303-10,
/// owner 2026-10-18: "меппинг должен сопровождаться временными тегами и группами вокруг обрабатываемых
/// компонентов"). They are painted on the canvas, not added as document objects, so nothing is saved
/// into the .gh and nothing enters the undo stack. A frame looks like a group behind the component, in
/// the colour of its least settled tag; the tags stand above it, one line per proposed component (a
/// calculation component with several measured outputs gets one line per output). Cleared once the
/// session is applied. UI thread only.
/// </summary>
internal sealed class MappingCanvasTags : IDisposable
{
    private const float FramePad = 8f;
    private const float TagHeight = 14f;
    private static readonly Font TagFont = new("Segoe UI", 7f, FontStyle.Bold);

    private GH_Document? _doc;
    private IReadOnlyList<MappingCanvasTag> _tags = Array.Empty<MappingCanvasTag>();
    private GH_Canvas? _canvas;

    public void Show(GH_Document? doc, IReadOnlyList<MappingCanvasTag> tags)
    {
        _doc = doc;
        _tags = tags ?? Array.Empty<MappingCanvasTag>();
        Attach();
        _canvas?.Refresh();
    }

    public void Clear()
    {
        if (_tags.Count == 0)
        {
            return;
        }

        _tags = Array.Empty<MappingCanvasTag>();
        _canvas?.Refresh();
    }

    public void Dispose()
    {
        _tags = Array.Empty<MappingCanvasTag>();
        var canvas = _canvas;
        Detach();
        canvas?.Refresh();
    }

    private void Attach()
    {
        var canvas = Instances.ActiveCanvas;
        if (ReferenceEquals(canvas, _canvas))
        {
            return;
        }

        Detach();
        _canvas = canvas;
        if (_canvas is null)
        {
            return;
        }

        _canvas.CanvasPostPaintGroups += OnPaintFrames;
        _canvas.CanvasPostPaintObjects += OnPaintTags;
    }

    private void Detach()
    {
        if (_canvas is null)
        {
            return;
        }

        _canvas.CanvasPostPaintGroups -= OnPaintFrames;
        _canvas.CanvasPostPaintObjects -= OnPaintTags;
        _canvas = null;
    }

    /// <summary>Most unsettled first: a frame takes the colour of its first state in this order.</summary>
    private static int Rank(string state) => state switch
    {
        "ambiguous" => 0,
        "suggested" => 1,
        "unmapped" => 2,
        "auto" => 3,
        _ => 4,
    };

    private sealed class Frame
    {
        public RectangleF Bounds;
        public string State = "confirmed";
        public readonly List<(MappingCanvasTag Tag, RectangleF? Part)> Rows = new();
    }

    private List<Frame> Layout(GH_Canvas canvas)
    {
        var frames = new List<Frame>();
        var doc = _doc;
        if (doc is null || _tags.Count == 0 || !ReferenceEquals(canvas.Document, doc))
        {
            return frames;
        }

        var byTop = new Dictionary<Guid, Frame>();
        foreach (var tag in _tags)
        {
            if (!Guid.TryParseExact(tag.ComponentId, "N", out var guid))
            {
                continue;
            }

            var obj = doc.FindObject(guid, false);
            var attributes = obj?.Attributes;
            var top = attributes?.GetTopLevel;
            if (attributes is null || top?.DocObject is null)
            {
                continue;
            }

            if (!byTop.TryGetValue(top.DocObject.InstanceGuid, out var frame))
            {
                frame = new Frame { Bounds = top.Bounds, State = tag.State };
                byTop[top.DocObject.InstanceGuid] = frame;
                frames.Add(frame);
            }

            if (Rank(tag.State) < Rank(frame.State))
            {
                frame.State = tag.State;
            }

            frame.Rows.Add((tag, ReferenceEquals(attributes, top) ? null : attributes.Bounds));
        }

        return frames;
    }

    private static RectangleF Outer(Frame frame)
    {
        var r = frame.Bounds;
        r.Inflate(FramePad, FramePad);
        var tagSpace = frame.Rows.Count * TagHeight + 2f;
        return new RectangleF(r.X, r.Y - tagSpace, r.Width, r.Height + tagSpace);
    }

    private void OnPaintFrames(GH_Canvas sender)
    {
        var g = sender.Graphics;
        foreach (var frame in Layout(sender))
        {
            var colour = MappingPreviewConduit.ColourOf(frame.State);
            using var path = Rounded(Outer(frame), 6f);
            using var fill = new SolidBrush(Color.FromArgb(48, colour));
            using var pen = new Pen(Color.FromArgb(220, colour), 2f) { DashStyle = DashStyle.Dash };
            g.FillPath(fill, path);
            g.DrawPath(pen, path);
        }
    }

    private void OnPaintTags(GH_Canvas sender)
    {
        var g = sender.Graphics;
        foreach (var frame in Layout(sender))
        {
            var outer = Outer(frame);
            for (var i = 0; i < frame.Rows.Count; i++)
            {
                var (tag, part) = frame.Rows[i];
                var colour = MappingPreviewConduit.ColourOf(tag.State);
                var size = g.MeasureString(tag.Text, TagFont);
                var box = new RectangleF(outer.X + 3f, outer.Y + 2f + i * TagHeight, Math.Max(size.Width + 6f, 20f), TagHeight - 2f);
                using (var path = Rounded(box, 3f))
                using (var fill = new SolidBrush(Color.FromArgb(235, colour)))
                {
                    g.FillPath(fill, path);
                }

                using (var text = new SolidBrush(Brightness(colour) > 0.6f ? Color.Black : Color.White))
                {
                    g.DrawString(tag.Text, TagFont, text, box.X + 3f, box.Y + (box.Height - size.Height) / 2f);
                }

                if (part is { } p)
                {
                    p.Inflate(1.5f, 1.5f);
                    using var pen = new Pen(colour, 2f);
                    g.DrawRectangle(pen, p.X, p.Y, p.Width, p.Height);
                }
            }
        }
    }

    private static float Brightness(Color c) => (0.299f * c.R + 0.587f * c.G + 0.114f * c.B) / 255f;

    private static GraphicsPath Rounded(RectangleF r, float radius)
    {
        var d = radius * 2f;
        var path = new GraphicsPath();
        path.AddArc(r.X, r.Y, d, d, 180, 90);
        path.AddArc(r.Right - d, r.Y, d, d, 270, 90);
        path.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
        path.AddArc(r.X, r.Bottom - d, d, d, 90, 90);
        path.CloseFigure();
        return path;
    }
}
#endif
