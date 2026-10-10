using System;
using UnityEditor;
using UnityEngine;

namespace Weapons.EditorTools
{
    /// <summary>
    /// Import settings for Assets/Weapons: models import as plain meshes, Read/Write on (a goblin merges its props into
    /// one mesh at run time, and particle effects emit from a weapon's surface), no materials (WeaponsSetup assigns
    /// them), the exported normals kept. T_Weapons and T_Shields are colour (sRGB); their _Glow and _MS maps are data
    /// (linear).
    /// </summary>
    class WeaponsPostprocessor : AssetPostprocessor
    {
        static bool Under(string path, string folder) =>
            path.Replace('\\', '/').IndexOf("Assets/Weapons/" + folder + "/", StringComparison.OrdinalIgnoreCase) == 0;

        void OnPreprocessModel()
        {
            if (!Under(assetPath, "Models") || !assetPath.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase)) return;
            var imp = (ModelImporter)assetImporter;
            imp.isReadable = true;
            imp.materialImportMode = ModelImporterMaterialImportMode.None;
            imp.importNormals = ModelImporterNormals.Import;
            imp.importTangents = ModelImporterTangents.CalculateMikk;
            imp.meshCompression = ModelImporterMeshCompression.Off;
            imp.animationType = ModelImporterAnimationType.None;
            imp.importAnimation = false;
            imp.importCameras = false;
            imp.importLights = false;
            imp.importBlendShapes = false;
            imp.generateSecondaryUV = false;
        }

        void OnPreprocessTexture()
        {
            if (!Under(assetPath, "Textures")) return;
            var imp = (TextureImporter)assetImporter;
            bool colour = assetPath.EndsWith("T_Weapons.png", StringComparison.OrdinalIgnoreCase)
                          || assetPath.EndsWith("T_Shields.png", StringComparison.OrdinalIgnoreCase);
            imp.sRGBTexture = colour;
            imp.alphaIsTransparency = false;
            imp.mipmapEnabled = true;
            imp.maxTextureSize = 2048;
            imp.textureCompression = TextureImporterCompression.CompressedHQ;
            if (colour)
                imp.alphaSource = TextureImporterAlphaSource.None;
        }
    }
}
