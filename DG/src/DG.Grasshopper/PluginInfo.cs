#if GRASSHOPPER_SDK
using Grasshopper.Kernel;
using System.Drawing;

namespace DG.Grasshopper;

public sealed class DGGrasshopperInfo : GH_AssemblyInfo
{
    public override string Name => "DG";

    public override Bitmap Icon => DgIcons.Metagraph24;

    public override string Description => "Design Grammars validation components for Neo4j + SWRL.";

    public override Guid Id => new("DA2CE289-78D5-4AD9-BC7E-EFDD7B2D06D5");

    public override string AuthorName => "DG";

    public override string AuthorContact => string.Empty;
}
#else
namespace DG.Grasshopper;

public sealed class DGGrasshopperInfo
{
}
#endif
