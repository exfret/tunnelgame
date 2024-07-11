package com.example.tunnelvision;

import java.awt.BorderLayout;
import java.awt.TextField;
import java.awt.Toolkit;
import java.awt.event.KeyAdapter;
import java.awt.event.KeyEvent;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.util.Scanner;

import javax.swing.BoxLayout;
import javax.swing.JButton;
import javax.swing.JCheckBoxMenuItem;
import javax.swing.JEditorPane;
import javax.swing.JFrame;
import javax.swing.JMenu;
import javax.swing.JMenuBar;
import javax.swing.JMenuItem;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;

public class JavaView extends JFrame {
    private JPanel buttonPanel;
    private JEditorPane textDisplayPane;
    private JScrollPane scrollPane;

    private JScrollPane secretScrollPane;
    private JPanel secretButtonPanel;
    private JMenuBar menuBar;
    private JMenu mnNewMenu;
    private JCheckBoxMenuItem chckbxmntmNewCheckItem;
    private TextField textField;

    public static String currentHTML = "";
    private JScrollPane scrollPane_1;
    private JMenuItem mntmNewMenuItem;
    private JMenuItem mntmNewMenuItem_1;

    public JavaView() {
        JavaView THIS = this;

        this.setSize(Toolkit.getDefaultToolkit().getScreenSize().width - 50,
                Toolkit.getDefaultToolkit().getScreenSize().height - 100);
        this.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        textDisplayPane = new JEditorPane("text/html", "<!DOCTYPE html>\r\n"
                + "<html>\r\n"
                + "<body>\r\n"
                + "\r\n"
                + "<h1>My First Heading</h1>\r\n"
                + "\r\n"
                + "<p>My first paragraph.</p>\r\n"
                + "\r\n"
                + "</body>\r\n"
                + "</html>\r\n"
                + "\r\n"
                + "");
        textDisplayPane.setEditable(false);
        // getContentPane().add(textDisplayPane, BorderLayout.CENTER);

        buttonPanel = new JPanel();

        scrollPane = new JScrollPane(buttonPanel);
        buttonPanel.setLayout(new BoxLayout(buttonPanel, BoxLayout.Y_AXIS));
        getContentPane().add(scrollPane, BorderLayout.EAST);

        secretButtonPanel = new JPanel();

        secretScrollPane = new JScrollPane(secretButtonPanel);
        secretButtonPanel.setLayout(new BoxLayout(secretButtonPanel, BoxLayout.Y_AXIS));
        getContentPane().add(secretScrollPane, BorderLayout.WEST);

        scrollPane_1 = new JScrollPane(textDisplayPane);
        getContentPane().add(scrollPane_1, BorderLayout.CENTER);

        menuBar = new JMenuBar();
        setJMenuBar(menuBar);

        mnNewMenu = new JMenu("Settings");
        menuBar.add(mnNewMenu);

        chckbxmntmNewCheckItem = new JCheckBoxMenuItem("Show flavor text");
        chckbxmntmNewCheckItem.setSelected(true);
        mnNewMenu.add(chckbxmntmNewCheckItem);

        mntmNewMenuItem = new JMenuItem("Show variable value");
        mntmNewMenuItem.addMouseListener(new MouseAdapter() {
            @Override
            public void mousePressed(MouseEvent e) {
                String varName = JOptionPane.showInputDialog(THIS,
                        "What variable bruv?", null);
                System.out.println("get variable " + varName);
            }
        });
        mnNewMenu.add(mntmNewMenuItem);

        mntmNewMenuItem_1 = new JMenuItem("RUN CONSOLE");
        mntmNewMenuItem_1.addMouseListener(new MouseAdapter() {
            @Override
            public void mousePressed(MouseEvent e) {
                String varName = JOptionPane.showInputDialog(THIS,
                        "What command bruv?", null);
                System.out.println(varName);
            }
        });

        mnNewMenu.add(mntmNewMenuItem_1);

        textField = new TextField();

        textField.addKeyListener(new KeyAdapter() {
            @Override
            public void keyPressed(KeyEvent e) {
                if (e.getKeyCode() == KeyEvent.VK_ENTER) {
                    System.out.println(textField.getText());
                    textField.setText("");
                }
            }
        });

        getContentPane().add(textField, BorderLayout.SOUTH);

        this.setVisible(true);
    }

    public static void main(String[] args) {
        // Comment this out when running, I only use this because it was running on save every time
        //return;

        JavaView win = new JavaView();

        Scanner scanner = new Scanner(System.in);

        while (true) {
            if (scanner.hasNextLine()) {
                win.addText(scanner.nextLine());

                String input = scanner.nextLine();

                String[] msg = input.split(":", 2);

                if (msg[0] == "print") {
                    win.addText("<p>" + msg[1] + "<br><br></p>");
                } else if (msg[0] == "choice") {
                    win.setOptions(msg[1].split(" "));
                }
            }
        }
    }

    public void setText(String text) {
        textDisplayPane.setText(text);
        currentHTML = text;
    }

    public void addText(String text) {
        textDisplayPane.setText(currentHTML + "\r\n" + text);
        currentHTML += "\r\n" + text;
    }

    public void setSecretOptions(String... options) {
        secretButtonPanel.removeAll();

        for (String option : options) {
            JButton btnNewButton = new JButton(option);
            btnNewButton.addMouseListener(new MouseAdapter() {
                @Override
                public void mousePressed(MouseEvent e) {
                    System.out.println(option);
                }
            });
            secretButtonPanel.add(btnNewButton);
        }
    }

    public void setOptions(String... options) {
        buttonPanel.removeAll();

        for (String option : options) {
            JButton btnNewButton = new JButton(option);
            btnNewButton.addMouseListener(new MouseAdapter() {
                @Override
                public void mousePressed(MouseEvent e) {
                    System.out.println(option);
                }
            });
            buttonPanel.add(btnNewButton);
        }
    }
}