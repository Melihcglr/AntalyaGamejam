using UnityEngine;
using UnityEngine.UI;

public class ShowImageOnClick : MonoBehaviour
{
    public Button nasiloynanirbuton; // Button referansı
    public Image nasiloynanirgorsel;   // Image referansı

    void Start()
    {
        // Button click eventine listener ekle
        nasiloynanirbuton.onClick.AddListener(OnButtonClick);

        // Başlangıçta görüntüyü gizle
        nasiloynanirgorsel.gameObject.SetActive(false);
    }

    void OnButtonClick()
    {
        // Butona tıklandığında görüntüyü göster
        nasiloynanirgorsel.gameObject.SetActive(true);
    }
}
