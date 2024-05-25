using UnityEngine;

public class PlayerMovement : MonoBehaviour
{
    // Oyuncu Hareketi
    private CharacterController controller;
    public float speed = 5f;
    public float sprintSpeed = 10f; // Koþma hýzý

    // Kamera Kontrolü
    private float xRotation = 0f;
    public float mouseSensitivity = 100f;

    // Dönüþ Limitleri
    private const float MAX_X_ROTATION = 50f;
    private const float MIN_X_ROTATION = 20f;

    // Zýplama ve Yerçekimi
    private Vector3 velocity;
    private float gravity = -9.81f;
    private bool isGround;

    public Transform groundChecker;
    public float groundCheckerRadius;
    public LayerMask obstacleLayer;
    public float jumpSpeed;

    // Zoom Kontrolü
    public Camera playerCamera;
    public float zoomSpeed = 2f;
    public float minZoom = 20f;
    public float maxZoom = 60f;

    private void Awake()
    {
        controller = GetComponent<CharacterController>();
        // Ýmleci Kilitle
        Cursor.visible = false;
        Cursor.lockState = CursorLockMode.Locked;
    }

    private void Update()
    {
        // Oyuncu Hareketi
        float currentSpeed = Input.GetKey(KeyCode.LeftShift) ? sprintSpeed : speed; // Shift tuþuna basýldýðýnda koþma hýzý uygula
        Vector3 moveInputs = Input.GetAxis("Horizontal") * Vector3.right + Input.GetAxis("Vertical") * Vector3.forward;
        Vector3 moveVelocity = transform.TransformDirection(moveInputs) * currentSpeed * Time.deltaTime;
        controller.Move(moveVelocity);

        // Kamera Kontrolü
        float mouseX = Input.GetAxis("Mouse X") * mouseSensitivity * Time.deltaTime;
        float mouseY = Input.GetAxis("Mouse Y") * mouseSensitivity * Time.deltaTime;

        xRotation -= mouseY;
        xRotation = Mathf.Clamp(xRotation, MIN_X_ROTATION, MAX_X_ROTATION);

        // Dönüþ açýlarýný uygulama
        transform.Rotate(Vector3.up * mouseX);
        Camera.main.transform.localRotation = Quaternion.Euler(xRotation, 0, 0);

        // Yerçekimi uygula ve zýplama
        ApplyGravity();

        // Zoom Kontrolü
        HandleZoom();
    }

    private void ApplyGravity()
    {
        // Yerde mi kontrol et
        isGround = Physics.CheckSphere(groundChecker.position, groundCheckerRadius, obstacleLayer);

        if (isGround && velocity.y < 0)
        {
            // Yere deðdiðinde düþmeyi durdur
            velocity.y = 0;
        }
        else
        {
            // Yere deðmediðinde yerçekimini uygula
            velocity.y += gravity * Time.deltaTime;
        }

        // Zýplama iþlevi
        if (Input.GetKeyDown(KeyCode.Space) && isGround)
        {
            velocity.y = Mathf.Sqrt(jumpSpeed * -2f * gravity);
        }

        // Yerçekimini uygula
        controller.Move(velocity * Time.deltaTime);
    }

    private void HandleZoom()
    {
        float scrollData = Input.GetAxis("Mouse ScrollWheel");
        playerCamera.fieldOfView -= scrollData * zoomSpeed;
        playerCamera.fieldOfView = Mathf.Clamp(playerCamera.fieldOfView, minZoom, maxZoom);
    }
}
